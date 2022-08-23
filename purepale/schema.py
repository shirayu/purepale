#!/usr/bin/env python3

from pydantic import BaseModel


class WebRequest(BaseModel):
    prompt: str


class WebResponse(BaseModel):
    path: str
