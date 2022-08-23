#!/usr/bin/env python3
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline
from torch.amp.autocast_mode import autocast


def get_max_index(p: Path):
    mx = 0
    for image in p.glob("*.png"):
        try:
            n: int = int(image.name.split(".")[0])
        except ValueError:
            continue
        mx = max(mx, n)
    return mx


# pipe = StableDiffusionPipeline.from_pretrained(model_id, use_auth_token=True)
# pipe = pipe.to(device)

with torch.no_grad():
    model_id = "CompVis/stable-diffusion-v1-4"
    print(f"Loading... {model_id}")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=True,
    )
    pipe.to("cuda")

    with Path("/dev/stdin").open("r") as inf, autocast("cuda"):
        print("Ready!")
        path_out = Path("img")
        path_out.mkdir(exist_ok=True, parents=True)
        idx = get_max_index(path_out)
        for line in inf:
            prompt: str = line.strip()
            if len(prompt) == 0:
                continue
            image = pipe(prompt)["sample"][0]
            oname: Path = path_out.joinpath(f"{idx:06}.png")
            idx += 1
            image.save(str(oname))
            print(f"Saved to {oname}")
