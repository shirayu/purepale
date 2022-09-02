#!/usr/bin/env python3

import random
from typing import Final, List

TILEABLE_COMMAND: Final[str] = "--tileable"
REPALCE_COMMAND: Final[str] = "--replace"

SET_START: Final[str] = "{"
SET_END: Final[str] = "}"
SET_SEPARATOR: Final[str] = "|"


class Prompt:
    original: str
    tileable: bool
    _parsed_str: str

    enable_replace: bool
    split_prompt: List[str] = []
    random_indices: List[int] = []
    random_list: List[List[str]] = []

    def __init__(self, *, original: str):
        self.original = original
        self._parsed_str = self.original
        self.tileable = False
        self.enable_replace = False

        if TILEABLE_COMMAND in self._parsed_str:
            self._parsed_str = self.original.replace(TILEABLE_COMMAND, "")
            self.tileable = True

        if REPALCE_COMMAND in self._parsed_str:
            self._parsed_str = self.original.replace(REPALCE_COMMAND, "")
            self.enable_replace = True

            self.split_prompt = self._parsed_str.split(SET_START)
            for idx, item in enumerate(self.split_prompt):
                if item.endswith(SET_END):
                    self.random_indices.append(idx)
                    wordset = item[: -len(SET_START)].split(SET_SEPARATOR)
                    self.random_list.append(wordset)

    def __call__(self) -> str:
        if not self.enable_replace:
            return "".join(self._parsed_str)

        tmp = self.split_prompt[:]
        for idx, myset in zip(self.random_indices, self.random_list):
            tmp[idx] = random.choice(myset)
        return "".join(tmp)
