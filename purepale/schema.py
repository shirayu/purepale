#!/usr/bin/env python3

from typing import Any, Optional

from pydantic import BaseModel


class Parameters(BaseModel):
    # Parameters for LDMTextToImagePipeline
    # diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion.py
    height: int = 512
    width: int = 512
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    eta: float = 0.0
    strength: float = 0.8


class PipesRequest(BaseModel):
    prompt: str
    initial_image: Optional[Any] = None
    initial_image_mask: Optional[Any] = None
    parameters: Parameters


class WebRequest(BaseModel):
    prompt: str
    path_initial_image: Optional[str] = None
    path_initial_image_mask: Optional[str] = None
    parameters: Parameters = Parameters()


class WebResponse(BaseModel):
    path: str


class Info(BaseModel):
    default_parameters: Parameters
