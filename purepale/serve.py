#!/usr/bin/env python3

import argparse
import random
import shutil
import uuid
from io import BytesIO
from pathlib import Path

import numpy as np
import PIL
import PIL.Image
import torch
import torch.backends.cudnn
import uvicorn
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from torch.amp.autocast_mode import autocast

from purepale.schema import Info, Parameters, WebRequest, WebResponse
from purepale.third_party.image_to_image import StableDiffusionImg2ImgPipeline, preprocess


def load_img(path):
    image = PIL.Image.open(path).convert("RGB")
    w, h = image.size
    print(f"loaded input image of size ({w}, {h}) from {path}")
    w, h = map(lambda x: x - x % 32, (w, h))  # resize to integer multiple of 32
    image = image.resize((w, h), resample=PIL.Image.LANCZOS)
    image = np.array(image).astype(np.float32) / 255.0
    image = image[None].transpose(0, 3, 1, 2)
    image = torch.from_numpy(image)
    return 2.0 * image - 1.0


def torch_fix_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms = True


def get_app(opts):
    path_out: Path = opts.output
    path_out.mkdir(exist_ok=True, parents=True)
    model_id = "CompVis/stable-diffusion-v1-4"
    print(f"Loading... {model_id}")

    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    pipe_txt2img = StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=True,
    ).to(device)

    pipe_img2img = StableDiffusionImg2ImgPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=True,
        # Re-use
        vae=pipe_txt2img.vae,
        text_encoder=pipe_txt2img.text_encoder,
        tokenizer=pipe_txt2img.tokenizer,
        unet=pipe_txt2img.unet,
        scheduler=pipe_txt2img.scheduler,
        feature_extractor=pipe_txt2img.feature_extractor,
    ).to("cuda")

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

    @app.post("/api/generate", response_model=WebResponse)
    def api_generate(request: WebRequest):
        with torch.no_grad():
            with autocast(device):
                try:
                    kwargs = {}
                    model = pipe_txt2img
                    if request.path_initial_image:
                        path_ii = path_out.joinpath(Path(request.path_initial_image).name)
                        if not path_ii.exists():
                            raise HTTPException(
                                status_code=400,
                                detail="File does not exist",
                            )

                        model = pipe_img2img
                        init_image = None
                        with path_ii.open("rb") as imgf:
                            init_image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
                        init_image = init_image.resize((request.parameters.height, request.parameters.width))
                        init_image = preprocess(init_image)
                        kwargs["init_image"] = init_image
                    else:
                        kwargs["height"] = request.parameters.height
                        kwargs["width"] = request.parameters.width

                    image = model(
                        request.prompt,
                        num_inference_steps=request.parameters.num_inference_steps,
                        guidance_scale=request.parameters.guidance_scale,
                        eta=request.parameters.eta,
                        **kwargs,
                    )["sample"][0]
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail="".join(e.args),
                    )

                name = str(uuid.uuid4())
                path_outfile: Path = path_out.joinpath(f"{name}.png")
                image.save(path_outfile)
        return WebResponse(
            path=f"images/{path_outfile.name}",
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

    oparser.add_argument(
        "--seed",
        type=int,
    )
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    if opts.seed is not None:
        torch_fix_seed(opts.seed)
    app = get_app(opts)
    uvicorn.run(
        app,  # type: ignore
        host=opts.host,
        port=opts.port,
        root_path=opts.root_path,
    )


if __name__ == "__main__":
    main()
