#!/usr/bin/env python3

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, validator


class ModelConfig(BaseModel):
    model_id: str
    revision: str
    dtype: Literal["fp16", "fp32"]

    @staticmethod
    def parse(query: str) -> "ModelConfig":
        r_at: int = query.rfind("@")
        dtype: Literal["fp16", "fp32"] = "fp16"
        if r_at >= 0:
            v: str = query[r_at + 1 :]
            assert v == "fp16" or v == "fp32", f"`{v}` is not acceptable"
            dtype: Literal["fp16", "fp32"] = v
            query = query[:r_at]
        _items: List[str] = query.split("/")
        assert 2 <= len(_items) <= 3
        revision: str = "main"
        if len(_items) == 3:
            revision = _items[2]
        model_id = "/".join(_items[:2])

        return ModelConfig(
            model_id=model_id,
            revision=revision,
            dtype=dtype,
        )


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


class PipesRequest(BaseModel):
    initial_image: Optional[Any] = None
    initial_image_mask: Optional[Any] = None
    parameters: Parameters


class WebRequest(BaseModel):
    model: str
    path_initial_image: Optional[str] = None
    path_initial_image_mask: Optional[str] = None
    parameters: Parameters = Parameters()

    @validator("path_initial_image_mask")
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
    model: ModelConfig
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
