#!/usr/bin/env python3

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class Parameters(BaseModel):
    # Parameters for LDMTextToImagePipeline
    # diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion.py
    prompt: str = ""
    height: int = 512
    width: int = 512
    num_inference_steps: int = 20
    guidance_scale: float = 7.5
    eta: float = 0.0
    strength: float = 0.8
    seed: Optional[int] = None


class ImageMask(BaseModel):
    a_x: int
    a_y: int
    b_x: int
    b_y: int


class PipesRequest(BaseModel):
    initial_image: Optional[Any] = None
    initial_image_mask: Optional[Any] = None
    parameters: Parameters


class WebRequest(BaseModel):
    model: str
    path_initial_image: Optional[str] = None
    initial_image_masks: Optional[List[ImageMask]] = None
    parameters: Parameters = Parameters()

    @validator("initial_image_masks")
    def mask(cls, v, values, **kwargs):
        if v is not None and values["path_initial_image"] is None:
            raise ValueError("Mask should be with original image")
        return v


class PrasedPrompt(BaseModel):
    used_prompt: str
    used_prompt_tokens: List[str]
    used_prompt_truncated: List[str]
    negative_prompt: str
    tileable: bool


class WebResponse(BaseModel):
    request: WebRequest
    model: str
    revision: str
    path: str
    scheduler: Dict[str, Any]
    parsed_prompt: PrasedPrompt


class WebImg2PromptRequest(BaseModel):
    path: str


class WebImg2PromptResponse(BaseModel):
    prompt: str


class Info(BaseModel):
    default_parameters: Parameters
    supported_models: List[str]
