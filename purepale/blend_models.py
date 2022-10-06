#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import List

import torch
from diffusers import DiffusionPipeline

from purepale.schema import ModelConfig

# from diffusers import StableDiffusionPipeline


def operation(models: List[str], weight: List[float], path_out: Path) -> None:
    assert len(models) >= 2
    assert sum(weight) == 1
    assert len(models) == len(models)
    out_pipe = None
    for j, model in enumerate(models):
        model_config: ModelConfig = ModelConfig.parse(model)
        pipe = DiffusionPipeline.from_pretrained(
            pretrained_model_name_or_path=model_config.model_id,
            revision=model_config.revision,
            torch_dtype=torch.float16 if model_config.dtype == "fp16" else torch.float32,
        )
        if j == 0:
            out_pipe = pipe

        assert out_pipe is not None
        for _m in [pipe.unet, pipe.vae]:
            _sd = _m.state_dict()
            for (target, v) in _m.named_parameters():
                if j == 0:
                    _sd[target] = v * weight[j] / 1.0
                else:
                    _sd[target] += v * weight[j] / 1.0
    assert out_pipe is not None
    out_pipe.save_pretrained(path_out)


def get_opts() -> argparse.Namespace:
    oparser = argparse.ArgumentParser()
    oparser.add_argument("--model", action="append", required=True)
    oparser.add_argument("--weight", "-w", type=float, action="append", required=True)
    oparser.add_argument("--output", "-o", type=Path, required=True)
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    operation(opts.model, opts.weight, opts.output)


if __name__ == "__main__":
    main()
