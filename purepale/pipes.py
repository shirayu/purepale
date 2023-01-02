from logging import getLogger
from typing import Any, Dict, Tuple

import PIL
import PIL.Image
import PIL.ImageDraw
import torch
import torch.backends.cudnn
from diffusers import (
    EulerDiscreteScheduler,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipelineLegacy,
    StableDiffusionPipeline,
)

from purepale.prompt import Prompt
from purepale.schema import ModelConfig, PipesRequest, PrasedPrompt

logger = getLogger(__name__)


class Pipes:
    @property
    def scheduler_param(self) -> Dict[str, Any]:
        return self.pipe_txt2img.scheduler.config

    def __init__(
        self,
        *,
        model_config: ModelConfig,
        device: str,
        nosafety: bool,
        slice_size: int,
        local_files_only: bool,
    ):
        self.device: str = device
        self.feature_egative_prompt: bool = False

        logger.info(f"Loading {model_config})")
        model_id: str = model_config.model_id
        logger.info(f"Finished loading of {model_config}")

        kwargs = {}
        if nosafety:
            kwargs["safety_checker"] = None

        self.pipe_txt2img = StableDiffusionPipeline.from_pretrained(
            model_id,
            revision=model_config.revision,
            torch_dtype=torch.float16 if model_config.dtype == "fp16" else torch.float32,
            local_files_only=local_files_only,
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

        self.pipe_masked_img2img = StableDiffusionInpaintPipelineLegacy(
            vae=self.pipe_txt2img.vae,
            text_encoder=self.pipe_txt2img.text_encoder,
            tokenizer=self.pipe_txt2img.tokenizer,
            unet=self.pipe_txt2img.unet,
            scheduler=self.pipe_txt2img.scheduler,
            feature_extractor=self.pipe_txt2img.feature_extractor,
            safety_checker=self.pipe_txt2img.safety_checker,
        ).to(device)

    def generate(
        self,
        *,
        request: PipesRequest,
    ) -> Tuple[PIL.Image.Image, PrasedPrompt]:
        assert request.parameters.seed is not None

        kwargs = {}
        model = self.pipe_txt2img
        if request.initial_image_mask is not None:
            model = self.pipe_masked_img2img
            kwargs["image"] = request.initial_image  # no preprocess
            kwargs["mask_image"] = request.initial_image_mask
            kwargs["strength"] = request.parameters.strength
        elif request.initial_image is not None:
            model = self.pipe_img2img
            kwargs["image"] = request.initial_image
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
        parsed_prompt = prompt.get_parsed(
            used_prompt=used_prompt,
            tokenizer=self.pipe_txt2img.tokenizer,
        )
        if self.feature_egative_prompt:
            kwargs["negative_prompt"] = prompt.negative

        with torch.no_grad():
            image = model(
                used_prompt,
                num_inference_steps=request.parameters.num_inference_steps,
                guidance_scale=request.parameters.guidance_scale,
                eta=request.parameters.eta,
                generator=generator,
                **kwargs,
            ).images[0]
        return image, parsed_prompt
