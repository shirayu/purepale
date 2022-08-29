
# 🎨 Purepale

[![CI](https://github.com/shirayu/purepale/actions/workflows/ci.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/ci.yml)
[![CodeQL](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml)
[![Typos](https://github.com/shirayu/purepale/actions/workflows/typos.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/typos.yml)

A simple web interface of image generations

## Setup

```bash
# Install with poetry
poetry install --no-dev

# Download torch for cuda
mkdir -p wheel
wget https://download.pytorch.org/whl/cu116/torch-1.12.1%2Bcu116-cp310-cp310-linux_x86_64.whl -P wheel
wget http://download.pytorch.org/whl/cu116/torchvision-0.13.1%2Bcu116-cp310-cp310-linux_x86_64.whl -P wheel
poetry run pip install wheels/*
```

## Run

```bash
poetry run python -m purepale.serve -o ~/IMG --port 8000
```

## Prompt options

- ``--tileable``: Make images tileable

## Documents

- [Tips to run on Linux in Windows WSL2](docs/wsl2.md)

## License

Apache License 2.0
