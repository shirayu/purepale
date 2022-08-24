#!/usr/bin/env python3

import argparse
import random
import uuid
from pathlib import Path

import numpy as np
import torch
import uvicorn
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from torch.amp.autocast_mode import autocast

from purepale.schema import Info, Parameters, WebRequest, WebResponse


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
    model = StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=True,
    ).to(device)

    app = FastAPI()
    app.mount("/images", StaticFiles(directory=str(path_out)), name="images")

    @app.post("/api/generate", response_model=WebResponse)
    def api_generate(request: WebRequest):
        with torch.no_grad():
            with autocast(device):
                image = model(
                    request.prompt,
                    height=request.parameters.height,
                    width=request.parameters.width,
                    num_inference_steps=request.parameters.num_inference_steps,
                    guidance_scale=request.parameters.guidance_scale,
                    eta=request.parameters.eta,
                )["sample"][0]
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
