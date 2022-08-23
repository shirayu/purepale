#!/usr/bin/env python3

import argparse
import uuid
from pathlib import Path

import torch
import uvicorn
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from torch.amp.autocast_mode import autocast

from purepale.schema import WebRequest, WebResponse


def get_app(opts):
    path_out: Path = opts.output
    path_out.mkdir(exist_ok=True, parents=True)
    model_id = "CompVis/stable-diffusion-v1-4"
    print(f"Loading... {model_id}")

    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=True,
    ).to("cuda")

    app = FastAPI()
    app.mount("/images", StaticFiles(directory=str(path_out)), name="images")

    @app.post("/api/generate", response_model=WebResponse)
    def api_generate(request: WebRequest):
        with torch.no_grad():
            with autocast("cuda"):
                image = pipe(request.prompt)["sample"][0]
                name = str(uuid.uuid4())
                path_outfile: Path = path_out.joinpath(f"{name}.png")
                image.save(path_outfile)
        return WebResponse(
            path=f"images/{path_outfile.name}",
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
