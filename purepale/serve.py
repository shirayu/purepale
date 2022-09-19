#!/usr/bin/env python3

import argparse
import datetime
import logging
import random
import shutil
import threading
import traceback
from io import BytesIO
from pathlib import Path
from typing import Optional

import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageOps
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
    ModelConfig,
    Parameters,
    PipesRequest,
    PurepaleFeatures,
    WebImg2PromptRequest,
    WebImg2PromptResponse,
    WebRequest,
    WebResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_app(opts):
    path_out: Path = opts.output
    path_out.mkdir(exist_ok=True, parents=True)

    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    model_blip: Optional[BLIP] = None
    logger.info(f"Features: {[v.value for v in opts.feature]}")
    if PurepaleFeatures.blip in opts.feature:
        logger.info("Loading BIIP")
        model_blip = BLIP(device)
        logger.info("Finished loading of BIIP")

    name2pipes = {}
    for name in opts.model:
        _pipes = Pipes(
            model_config=ModelConfig.parse(name),
            device=device,
            nosafety=opts.no_safety,
            slice_size=opts.slice_size,
        )
        if PurepaleFeatures.negative in opts.feature:
            _pipes.feature_egative_prompt = True
        name2pipes[name] = _pipes

    app = FastAPI()
    app.mount("/images", StaticFiles(directory=str(path_out)), name="images")
    semaphore = threading.Semaphore(opts.max_process)

    def generate_file_name_preifix() -> str:
        n: int = random.randint(0, 10000)
        return datetime.datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S_{n:05}")

    @app.post("/api/upload")
    async def upload(file: UploadFile):
        name: str = generate_file_name_preifix()
        outfile_name = f"uploaded_{name}{Path(file.filename).suffix}"
        path_outfile: Path = path_out.joinpath(outfile_name)
        with path_outfile.open("wb") as outf:
            shutil.copyfileobj(file.file, outf)
        return {"path": f"images/{outfile_name}"}

    @app.post("/api/img2prompt", response_model=WebImg2PromptResponse)
    def api_img2prompt(request: WebImg2PromptRequest):
        if model_blip is None:
            raise HTTPException(
                status_code=400,
                detail="BLIP is disabled",
            )

        path_ii = path_out.joinpath(Path(request.path).name)
        if not path_ii.exists():
            raise FileNotFoundError(f"Not Found: {request.path}")
        with path_ii.open("rb") as imgf:
            image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
            prompt: str = model_blip.predict(image)
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
            if request.path_initial_image:
                path_ii: Path = path_out.joinpath(Path(request.path_initial_image).name)
                if not path_ii.exists():
                    raise FileNotFoundError(f"Not Found: {request.path_initial_image}")
                with path_ii.open("rb") as imgf:
                    init_image = PIL.Image.open(BytesIO(imgf.read())).convert("RGB")
                init_image = init_image.resize((request.parameters.width, request.parameters.height))

            mask_img = None
            if request.path_initial_image_mask is not None:
                path_ii_mask: Path = path_out.joinpath(Path(request.path_initial_image_mask).name)
                if not path_ii_mask.exists():
                    raise FileNotFoundError(f"Not Found: {request.path_initial_image}")
                with path_ii_mask.open("rb") as imgf:
                    im = PIL.Image.open(BytesIO(imgf.read()))
                    if im.mode == "RGBA":
                        _, _, _, a = im.split()
                        im = PIL.Image.merge("RGB", (a, a, a))
                    else:
                        im = PIL.ImageOps.invert(im)
                    mask_img = im.convert("L")
                mask_img = mask_img.resize((request.parameters.width, request.parameters.height))

            if request.parameters.seed is None:
                request.parameters.seed = random.randint(-9007199254740991, 9007199254740991)

            with semaphore:
                image, parsed_prompt = pipes.generate(
                    request=PipesRequest(
                        initial_image=init_image,
                        initial_image_mask=mask_img,
                        parameters=request.parameters,
                    )
                )
                out_name_prefix: str = generate_file_name_preifix()

        except Exception as e:
            tr: str = "\n".join(list(traceback.TracebackException.from_exception(e).format()))
            raise HTTPException(
                status_code=400,
                detail="".join(e.args) + "\n" + tr,
            )

        path_outfile: Path = path_out.joinpath(f"{out_name_prefix}.png")
        image.save(path_outfile)

        resp = WebResponse(
            request=request,
            model=ModelConfig.parse(name),
            path=f"images/{path_outfile.name}",
            scheduler=pipes.scheduler_param,
            parsed_prompt=parsed_prompt,
        )
        path_log: Path = path_out.joinpath(f"{out_name_prefix}.json")
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
            supported_models=list(name2pipes.keys()),
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
        "--feature",
        "-f",
        action="append",
        type=PurepaleFeatures,
        help="Enable BILP",
        default=[],
        choices=list(PurepaleFeatures),
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
