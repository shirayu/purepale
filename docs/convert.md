
# Convert models

## ckpt to diffusers models

```bash
poetry run python .venv/src/diffusers/scripts/convert_original_stable_diffusion_to_diffusers.py \
    --checkpoint_path /path/to/model.ckpt \
    --dump_path /path/to/output
    --original_config_file ~/data/stable-diffusion/v1-inference.yaml \
```

``--original_config_file`` is optional. If you omit it, the file will be automatically downloaded.
