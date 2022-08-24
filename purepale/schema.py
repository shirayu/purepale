#!/usr/bin/env python3

from pydantic import BaseModel


class Parameters(BaseModel):
    # Parameters for LDMTextToImagePipeline
    height: int = 512
    width: int = 512
    num_inference_steps: int = 50
    guidance_scale: float = 1.0
    eta: float = 0.0


class WebRequest(BaseModel):
    prompt: str
    parameters: Parameters = Parameters()


class WebResponse(BaseModel):
    path: str


class Info(BaseModel):
    default_parameters: Parameters
