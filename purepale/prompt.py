#!/usr/bin/env python3

import random
from typing import Final, List

TILEABLE_COMMAND: Final[str] = "--tile"
REPALCE_COMMAND: Final[str] = "--random"

SET_START: Final[str] = "{"
SET_END: Final[str] = "}"
SET_SEPARATOR: Final[str] = "|"


class Prompt:
    original: str
    tileable: bool
    _parsed_str: str

    enable_replace: bool
    split_prompt: List[str]
    random_indices: List[int]
    random_list: List[List[str]]

    def __init__(self, *, original: str):
        self.original = original
        self._parsed_str = self.original
        self.tileable = False
        self.enable_replace = False

        if TILEABLE_COMMAND in self._parsed_str:
            self._parsed_str = self._parsed_str.replace(TILEABLE_COMMAND, "")
            self.tileable = True

        if REPALCE_COMMAND in self._parsed_str:
            self._parsed_str = self._parsed_str.replace(REPALCE_COMMAND, "")
            self.enable_replace = True
            self.split_prompt = []
            self.random_indices = []
            self.random_list = []

            for item in self._parsed_str.split(SET_START):
                sep_pos: int = item.find(SET_END)
                if sep_pos < 0:
                    self.split_prompt.append(item)
                    continue

                wordset: List[str] = item[:sep_pos].split(SET_SEPARATOR)

                if len(wordset) >= 2:
                    self.random_indices.append(len(self.split_prompt))
                    self.split_prompt.append("*")
                    self.random_list.append(wordset)
                else:
                    self.split_prompt.append(item[:sep_pos])

                if len(item) - (sep_pos + 1) > 0:
                    tail: str = item[sep_pos + 1 :]
                    self.split_prompt.append(tail)

    def __call__(self) -> str:
        if not self.enable_replace:
            return "".join(self._parsed_str)

        tmp = self.split_prompt[:]
        for idx, myset in zip(self.random_indices, self.random_list):
            tmp[idx] = random.choice(myset)
        return "".join(tmp)
