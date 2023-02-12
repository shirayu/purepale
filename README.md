
# 🎨 Purepale

[![CI](https://github.com/shirayu/purepale/actions/workflows/ci.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/ci.yml)
[![CodeQL](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml)
[![Typos](https://github.com/shirayu/purepale/actions/workflows/typos.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/typos.yml)

A simple web interface of image generations

![Screenshot](https://user-images.githubusercontent.com/963961/189476775-87a4c8b2-8959-4582-8708-7282e30091b2.png)

## Setup

```bash
pip install -U git+https://github.com/shirayu/whispering.git

# If you use GPU, install proper torch and torchvision
# Example : torch for CUDA 11.6
pip install -U torch torchvision --extra-index-url https://download.pytorch.org/whl/cu116
```

## Features

- Infinite generation mode
- [img2txt](https://twitter.com/shirayu/status/1564242586738790406)
- [img2img](https://twitter.com/shirayu/status/1563138353201291266)
- [masked_img2img](https://twitter.com/shirayu/status/1563466297668935680)
- Automatic JSON logging of queries

## Run

```bash
purepale -o ~/IMG --port 8000 --model CompVis/stable-diffusion-v1-4/fp16
```

- ``--model``: You can use multiple models
    - Format: ``model_path@dtype`` or ``org_name/model_name/revision@dtype`` (eg. ``naclbit/trinart_stable_diffusion_v2/diffusers-60k@fp16``, ``/path/to/model_dir@fp32``)
    - ``revision`` and ``dtype`` can be omitted
- ``--feature blip``: Enable BLIP (caption model)
- ``--slice-size``: Enable attention slicing with given number

Check full options with ``purepale -h``.

## Prompt options

- ``--tile``: [Make images tile](https://twitter.com/shirayu/status/1563907466131537920)
- ``--random``: Choice words randomly (eg: ``{Girl|Boy} with a {red|blue|green} {hat|box} --random``)

## Documents

- [Tips to run on Linux in Windows WSL2](https://gist.github.com/shirayu/8f54a16ce0de315908f1fdb419479aa8)
- [Convert models](docs/convert.md)

## License

Apache License 2.0
