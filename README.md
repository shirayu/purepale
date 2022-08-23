
# Purepale

A simple web interface of image generations

## Setup

```bash
wget https://download.pytorch.org/whl/cu116/torch-1.12.1%2Bcu116-cp310-cp310-linux_x86_64.whl -P wheel
poetry install --no-dev
```

## Run

```bash
poetry run python -m purepale.serve -o /dev/shm/IMG --port 8000
```

## License

Apache License 2.0
