
# 🎨 Purepale

[![CI](https://github.com/shirayu/purepale/actions/workflows/ci.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/ci.yml)
[![CodeQL](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/codeql-analysis.yml)
[![Typos](https://github.com/shirayu/purepale/actions/workflows/typos.yml/badge.svg)](https://github.com/shirayu/purepale/actions/workflows/typos.yml)

A simple web interface of image generations

## Setup

```bash
# Download torch for cuda
wget https://download.pytorch.org/whl/cu116/torch-1.12.1%2Bcu116-cp310-cp310-linux_x86_64.whl -P wheel

## If you want to use pytorch in PyPI, run the following command
## python .github/fix_poetry_for_ci.py | xargs -t poetry add

# Install with poetry
poetry install --no-dev
```

## Run

```bash
poetry run python -m purepale.serve -o ~/IMG --port 8000
```

## Documents

- [Tips to run on WSL2](docs/wsl2.md)

## License

Apache License 2.0
