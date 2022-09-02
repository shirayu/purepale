#!/usr/bin/env python3

from typing import Final

TILEABLE_COMMAND: Final[str] = "--tileable"


class Prompt:
    original: str
    tileable: bool
    parsed: str

    def __init__(self, *, original: str):
        self.original = original
        self.tileable = False

        if TILEABLE_COMMAND in self.original:
            self.parsed = self.original.replace(TILEABLE_COMMAND, "")
            self.tileable = True

    def __call__(self):
        return self.parsed
