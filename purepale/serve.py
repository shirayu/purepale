#!/usr/bin/env python3

import argparse
import random
import shutil
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import PIL
import PIL.Image
import PIL.ImageDraw
import torch
import torch.backends.cudnn
import uvicorn
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from torch.amp.autocast_mode import autocast
from torchvision import transforms
from torchvision.transforms.functional import InterpolationMode

from purepale.schema import (
    Info,
    Parameters,
    PipesRequest,
    WebImg2PromptRequest,
    WebImg2PromptResponse,
    WebRequest,
    WebResponse,
)
from purepale.third_party.blip.blip import blip_decoder
from purepale.third_party.image_to_image import StableDiffusionImg2ImgPipeline, preprocess
from purepale.third_party.inpainting import StableDiffusionInpaintingPipeline

TILEABLE_COMMAND: str = "--tileable"


class BLIP:
    def __init__(self, device: str):
        self.device = device
        self.blip_image_eval_size: int = 384
        blip_model_url = (
            "https://storage.googleapis.com/sfr-vision-language-research/BLIP/models/model*_base_caption.pth"
        )
        blip_model = blip_decoder(
            med_config=str(Path(__file__).parent.joinpath("third_party/blip/med_config.json")),
            pretrained=blip_model_url,
            image_size=self.blip_image_eval_size,
            vit="base",
        )
        blip_model.eval()
        self.blip_model = blip_model.to(device)

    def predict(self, image):
        gpu_image = (
            transforms.Compose(
                [
                    transforms.Resize(
                        (self.blip_image_eval_size, self.blip_image_eval_size),
                        interpolation=InterpolationMode.BICUBIC,
                    ),
                    transforms.ToTensor(),
                    transforms.Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
                ]
            )(image)
            .unsqueeze(0)
            .to(self.device)
        )

        with torch.no_grad():
            caption = self.blip_model.generate(
                gpu_image,
                sample=False,
                num_beams=3,
                max_length=20,
                min_length=5,
            )
        return caption[0]


class Pipes:
    def __init__(
        self,
        *,
        model_id: str,
        device: str,
    ):
        self.device = device

        print("Loading... BIIP")
        self.blip = BLIP(device)

        print(f"Loading... {model_id}")
        self.pipe_txt2img = StableDiffusionPipeline.from_pretrained(
            model_id,
            revision="fp16",
            torch_dtype=torch.float16,
            use_auth_token=True,
        ).to(device)

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

        self.pipe_img2img = StableDiffusionImg2ImgPipeline.from_pretrained(
            model_id,
            revision="fp16",
            torch_dtype=torch.float16,
            use_auth_token=True,
            # Re-use
            vae=self.pipe_txt2img.vae,
            text_encoder=self.pipe_txt2img.text_encoder,
            tokenizer=self.pipe_txt2img.tokenizer,
            unet=self.pipe_txt2img.unet,
            scheduler=self.pipe_txt2img.scheduler,
            feature_extractor=self.pipe_txt2img.feature_extractor,
        ).to(device)

        self.pipe_masked_img2img = StableDiffusionInpaintingPipeline(
            # Re-use
            vae=self.pipe_txt2img.vae,
            text_encoder=self.pipe_txt2img.text_encoder,
            tokenizer=self.pipe_txt2img.tokenizer,
            unet=self.pipe_txt2img.unet,
            scheduler=self.pipe_txt2img.scheduler,
            safety_checker=self.pipe_txt2img.safety_checker,
            feature_extractor=self.pipe_txt2img.feature_extractor,
        ).to(device)

    def generate(
        self,
        *,
        request: PipesRequest,
    ):
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
            init_image_tensor = preprocess(request.initial_image)
            kwargs["init_image"] = init_image_tensor
            kwargs["strength"] = request.parameters.strength
        else:
            kwargs["height"] = request.parameters.height
            kwargs["width"] = request.parameters.width

        tileable: bool = False
        original_prompt: str = request.parameters.prompt
        if TILEABLE_COMMAND in request.parameters.prompt:
            request.parameters.prompt = request.parameters.prompt.replace(TILEABLE_COMMAND, "")
            tileable = True
        for cl, opad in zip(self.conv_layers, self.conv_layers_original_paddings):
            if tileable:
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
        with torch.no_grad():
            with autocast(self.device):
                image = model(
                    request.parameters.prompt,
                    num_inference_steps=request.parameters.num_inference_steps,
                    guidance_scale=request.parameters.guidance_scale,
                    eta=request.parameters.eta,
                    generator=generator,
                    **kwargs,
                )["sample"][0]
        request.parameters.prompt = original_prompt
        return image


def get_app(opts):
    path_out: Path = opts.output
    path_out.mkdir(exist_ok=True, parents=True)

    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    pipes = Pipes(
        model_id=opts.model,
        device=device,
    )

    app = FastAPI()
    app.mount("/images", StaticFiles(directory=str(path_out)), name="images")

    @app.post("/api/upload")
    async def upload(file: UploadFile):
        # TODO: check the file is image
        name = str(uuid.uuid4())
        outfile_name = f"uploaded__{name}"
        path_outfile: Path = path_out.joinpath(outfile_name)
        with path_outfile.open("wb") as outf:
            shutil.copyfileobj(file.file, outf)
        return {"path": f"images/{outfile_name}"}

    @app.post("/api/img2prompt", response_model=WebImg2PromptResponse)
    def api_img2prompt(request: WebImg2PromptRequest):
        path_ii = path_out.joinpath(Path(request.path).name)
        if not path_ii.exists():
            raise FileNotFoundError(f"Not Found: {request.path}")
        with path_ii.open("rb") as imgf:
            image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
            prompt: str = pipes.blip.predict(image)
        return WebImg2PromptResponse(
            prompt=prompt,
        )

    @app.post("/api/generate", response_model=WebResponse)
    def api_generate(request: WebRequest):
        try:
            init_image = None
            orig_img_size = None
            if request.path_initial_image:
                path_ii: Optional[Path] = None
                path_ii = path_out.joinpath(Path(request.path_initial_image).name)
                if not path_ii.exists():
                    raise FileNotFoundError(f"Not Found: {request.path_initial_image}")
                with path_ii.open("rb") as imgf:
                    init_image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
                    orig_img_size = init_image.size[:]
                init_image = init_image.resize((request.parameters.height, request.parameters.width))

            mask_img = None
            if request.initial_image_masks is not None:
                path_ii: Optional[Path] = None
                # TODO: Make StableDiffusionInpaintingPipeline accept mask info directly
                assert orig_img_size is not None
                mask_img = PIL.Image.new("L", orig_img_size, 0)
                draw = PIL.ImageDraw.Draw(mask_img)
                for mask in request.initial_image_masks:
                    draw.rectangle(
                        (mask.a_x, mask.a_y, mask.b_x, mask.b_y),
                        fill=255,
                    )
                mask_img = mask_img.resize((request.parameters.height, request.parameters.width))

            if request.parameters.seed is None:
                request.parameters.seed = random.randint(-9007199254740991, 9007199254740991)

            out_name = str(uuid.uuid4())
            path_log: Path = path_out.joinpath(f"{out_name}.json")
            with path_log.open("w") as outlogf:
                outlogf.write(request.json(indent=4))
                outlogf.write("\n")

            image = pipes.generate(
                request=PipesRequest(
                    initial_image=init_image,
                    initial_image_mask=mask_img,
                    parameters=request.parameters,
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="".join(e.args),
            )

        path_outfile: Path = path_out.joinpath(f"{out_name}.png")
        image.save(path_outfile)
        return WebResponse(
            path=f"images/{path_outfile.name}",
            parameters=request.parameters,
        )

    @app.get("/api/info", response_model=Info)
    def api_info():
        dp = Parameters()
        return Info(
            default_parameters=dp,
        )

    app.mount(
        "/",
        StaticFiles(
            directory=Path(__file__).parent.joinpath("static"),
            html=True,
        ),
        name="static",
    )

    return app


def get_opts() -> argparse.Namespace:
    oparser = argparse.ArgumentParser()
    oparser.add_argument(
        "--model",
        default="CompVis/stable-diffusion-v1-4",
    )
    oparser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
    )

    oparser.add_argument(
        "--host",
        default="0.0.0.0",
    )
    oparser.add_argument(
        "--port",
        default=8000,
        type=int,
    )
    oparser.add_argument(
        "--root_path",
        default="",
    )
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    app = get_app(opts)
    uvicorn.run(
        app,  # type: ignore
        host=opts.host,
        port=opts.port,
        root_path=opts.root_path,
    )


if __name__ == "__main__":
    main()
