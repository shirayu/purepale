#!/usr/bin/env python3

import argparse
import random
import shutil
import threading
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Optional

import PIL
import PIL.Image
import PIL.ImageDraw
import torch
import torch.backends.cudnn
import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from purepale.blip import BLIP
from purepale.pipes import Pipes
from purepale.schema import (
    Info,
    Parameters,
    PipesRequest,
    WebImg2PromptRequest,
    WebImg2PromptResponse,
    WebRequest,
    WebResponse,
)


def get_app(opts):
    path_out: Path = opts.output
    path_out.mkdir(exist_ok=True, parents=True)

    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    blip: Optional[BLIP] = None
    if opts.blip:
        print("Loading... BIIP")
        blip = BLIP(device)

    name2pipes = {}
    for name in opts.model:
        _items: List[str] = name.split("/")
        assert 2 <= len(_items) <= 3
        _revision: str = "main"
        if len(_items) == 3:
            _revision = _items[2]

        _pipes = Pipes(
            model_id="/".join(_items[:2]),
            revision=_revision,
            device=device,
            nosafety=opts.no_safety,
            slice_size=opts.slice_size,
        )
        name2pipes[name] = _pipes

    app = FastAPI()
    app.mount("/images", StaticFiles(directory=str(path_out)), name="images")
    semaphore = threading.Semaphore(opts.max_process)

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
        if blip is None:
            raise HTTPException(
                status_code=400,
                detail="BLIP is disabled",
            )

        path_ii = path_out.joinpath(Path(request.path).name)
        if not path_ii.exists():
            raise FileNotFoundError(f"Not Found: {request.path}")
        with path_ii.open("rb") as imgf:
            image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
            prompt: str = blip.predict(image)
        return WebImg2PromptResponse(
            prompt=prompt,
        )

    @app.post("/api/generate", response_model=WebResponse)
    def api_generate(request: WebRequest):
        pipes = name2pipes.get(request.model)
        if pipes is None:
            return HTTPException(
                status_code=400,
                detail="Unsupported model name",
            )

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

            with semaphore:
                image, used_prompt = pipes.generate(
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

        out_name = str(uuid.uuid4())
        path_outfile: Path = path_out.joinpath(f"{out_name}.png")
        image.save(path_outfile)

        used_prompt_tokens, used_prompt_truncated = pipes.tokenize(used_prompt)
        resp = WebResponse(
            path=f"images/{path_outfile.name}",
            parameters=request.parameters,
            used_prompt=used_prompt,
            used_prompt_tokens=used_prompt_tokens,
            used_prompt_truncated=used_prompt_truncated,
        )
        path_log: Path = path_out.joinpath(f"{out_name}.json")
        with path_log.open("w") as outlogf:
            outlogf.write(
                resp.json(
                    indent=4,
                    ensure_ascii=False,
                )
            )
            outlogf.write("\n")
        return resp

    @app.get("/api/info", response_model=Info)
    def api_info():
        dp = Parameters()
        return Info(
            default_parameters=dp,
            suppoted_models=list(name2pipes.keys()),
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
    oparser.add_argument("--model", action="append", required=True)
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
        "--max_process",
        "-P",
        default=1,
        type=int,
    )
    oparser.add_argument(
        "--no-safety",
        action="store_true",
        help="Disable safety_checker with your responsibility",
    )
    oparser.add_argument(
        "--blip",
        action="store_true",
        help="Enable BILP",
    )
    oparser.add_argument(
        "--slice-size",
        type=int,
        help="0 means auto, Negative number means disabled. Large number saves VRAM but makes slow.",
        default=0,
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
