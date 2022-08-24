#!/usr/bin/env python3

from pydantic import BaseModel


class Parameters(BaseModel):
    # Parameters for LDMTextToImagePipeline
    # diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion.py
    height: int = 512
    width: int = 512
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    eta: float = 0.0


class WebRequest(BaseModel):
    prompt: str
    parameters: Parameters = Parameters()


class WebResponse(BaseModel):
    path: str


class Info(BaseModel):
    default_parameters: Parameters
