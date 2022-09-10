#!/usr/bin/env python3


from pathlib import Path

import torch
import torch.backends.cudnn
from torchvision import transforms
from torchvision.transforms.functional import InterpolationMode

from purepale.third_party.blip.blip import blip_decoder


class BLIP:
    def __init__(self, device: str):
        self.device: str = device
        self.blip_image_eval_size: int = 384
        blip_model_url = (
            "https://storage.googleapis.com/sfr-vision-language-research/BLIP/models/model*_base_caption.pth"
        )
        blip_model = blip_decoder(
            med_config=str(Path(__file__).parent.joinpath("third_party/blip/med_config.json")),
            pretrained=blip_model_url,
            image_size=self.blip_image_eval_size,
            vit="base",
        )
        blip_model.eval()
        self.blip_model = blip_model.to(device)

    def predict(self, image):
        gpu_image = (
            transforms.Compose(
                [
                    transforms.Resize(
                        (self.blip_image_eval_size, self.blip_image_eval_size),
                        interpolation=InterpolationMode.BICUBIC,
                    ),
                    transforms.ToTensor(),
                    transforms.Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
                ]
            )(image)
            .unsqueeze(0)
            .to(self.device)
        )

        with torch.no_grad():
            caption = self.blip_model.generate(
                gpu_image,
                sample=False,
                num_beams=3,
                max_length=20,
                min_length=5,
            )
        return caption[0]
