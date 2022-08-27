#!/usr/bin/env python3

from typing import Any, List, Optional

from pydantic import BaseModel, validator


class Parameters(BaseModel):
    # Parameters for LDMTextToImagePipeline
    # diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion.py
    height: int = 512
    width: int = 512
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    eta: float = 0.0
    strength: float = 0.8


class ImageMask(BaseModel):
    a_x: int
    a_y: int
    b_x: int
    b_y: int


class PipesRequest(BaseModel):
    prompt: str
    initial_image: Optional[Any] = None
    initial_image_mask: Optional[Any] = None
    parameters: Parameters


class WebRequest(BaseModel):
    prompt: str
    path_initial_image: Optional[str] = None
    initial_image_masks: Optional[List[ImageMask]] = None
    parameters: Parameters = Parameters()

    @validator("path_initial_image_mask")
    def mask(cls, v, values, **kwargs):
        if v is not None and values["path_initial_image"] is None:
            raise ValueError("Mask should be with original image")
        return v


class WebResponse(BaseModel):
    path: str


class Info(BaseModel):
    default_parameters: Parameters
