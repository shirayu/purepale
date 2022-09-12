#!/usr/bin/env python3

from typing import Any, Dict, List, Tuple

import PIL
import PIL.Image
import PIL.ImageDraw
import torch
import torch.backends.cudnn
from diffusers import (
    DDIMScheduler,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionPipeline,
)
from torch.amp.autocast_mode import autocast

from purepale.prompt import Prompt
from purepale.schema import PipesRequest


class Pipes:
    @property
    def scheduler_param(self) -> Dict[str, Any]:
        return self.pipe_txt2img.scheduler.config

    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        device: str,
        nosafety: bool,
        slice_size: int,
    ):
        self.device: str = device

        print(f"Loading... {model_id}")
        self.model_id: str = model_id
        self.revision: str = revision
        kwargs = {}
        if model_id == "hakurei/waifu-diffusion":
            kwargs["scheduler"] = DDIMScheduler(
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
            )

        self.pipe_txt2img = StableDiffusionPipeline.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=torch.float16 if revision == "fp16" else torch.float32,
            use_auth_token=True,
            **kwargs,
        ).to(device)
        if slice_size >= 0:
            self.pipe_txt2img.enable_attention_slicing(
                slice_size="auto" if slice_size == 0 else None if slice_size < 0 else slice_size,
            )

        targets = [
            self.pipe_txt2img.vae,
            self.pipe_txt2img.text_encoder,
            self.pipe_txt2img.unet,
        ]
        self.conv_layers = []
        self.conv_layers_original_paddings = []
        for target in targets:
            for module in target.modules():
                if isinstance(module, torch.nn.Conv2d) or isinstance(module, torch.nn.ConvTranspose2d):
                    self.conv_layers.append(module)
                    self.conv_layers_original_paddings.append(module.padding_mode)

        self.pipe_img2img = StableDiffusionImg2ImgPipeline(
            vae=self.pipe_txt2img.vae,
            text_encoder=self.pipe_txt2img.text_encoder,
            tokenizer=self.pipe_txt2img.tokenizer,
            unet=self.pipe_txt2img.unet,
            scheduler=self.pipe_txt2img.scheduler,
            feature_extractor=self.pipe_txt2img.feature_extractor,
            safety_checker=self.pipe_txt2img.safety_checker,
        ).to(device)

        self.pipe_masked_img2img = StableDiffusionInpaintPipeline(
            vae=self.pipe_txt2img.vae,
            text_encoder=self.pipe_txt2img.text_encoder,
            tokenizer=self.pipe_txt2img.tokenizer,
            unet=self.pipe_txt2img.unet,
            scheduler=self.pipe_txt2img.scheduler,
            feature_extractor=self.pipe_txt2img.feature_extractor,
            safety_checker=self.pipe_txt2img.safety_checker,
        ).to(device)

        if nosafety:
            del self.pipe_txt2img.safety_checker
            self.pipe_txt2img.safety_checker = lambda images, **kwargs: (images, False)
            self.pipe_img2img.safety_checker = lambda images, **kwargs: (images, False)
            self.pipe_masked_img2img.safety_checker = lambda images, **kwargs: (images, False)

    # TODO avoid tokenize twice for generation
    def tokenize(self, text: str) -> Tuple[List[str], List[str]]:
        tokens = self.pipe_txt2img.tokenizer.tokenize(
            text,
        )
        return tokens, tokens[self.pipe_txt2img.tokenizer.model_max_length :]

    def generate(
        self,
        *,
        request: PipesRequest,
    ) -> Tuple[PIL.Image.Image, str]:
        assert request.parameters.seed is not None

        kwargs = {}
        model = self.pipe_txt2img
        if request.initial_image_mask is not None:
            model = self.pipe_masked_img2img
            kwargs["init_image"] = request.initial_image  # no preprocess
            kwargs["mask_image"] = request.initial_image_mask
            kwargs["strength"] = request.parameters.strength
        elif request.initial_image is not None:
            model = self.pipe_img2img
            kwargs["init_image"] = request.initial_image
            kwargs["strength"] = request.parameters.strength
        else:
            kwargs["height"] = request.parameters.height
            kwargs["width"] = request.parameters.width

        prompt: Prompt = Prompt(
            original=request.parameters.prompt,
        )
        for cl, opad in zip(self.conv_layers, self.conv_layers_original_paddings):
            if prompt.tileable:
                # This hack is based on lox9973's snippet
                # https://gitlab.com/-/snippets/2395088
                cl.padding_mode = "circular"
            else:
                cl.padding_mode = opad

        generator = None
        if self.device == "cpu":
            generator = torch.manual_seed(request.parameters.seed)
        else:
            generator = torch.cuda.manual_seed(request.parameters.seed)

        used_prompt: str = prompt()
        with torch.no_grad():
            with autocast(self.device):
                image = model(
                    used_prompt,
                    num_inference_steps=request.parameters.num_inference_steps,
                    guidance_scale=request.parameters.guidance_scale,
                    eta=request.parameters.eta,
                    generator=generator,
                    **kwargs,
                ).images[0]
        return image, used_prompt
