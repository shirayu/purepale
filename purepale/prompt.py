#!/usr/bin/env python3

import random
from typing import Final, List

from purepale.schema import PrasedPrompt

TILEABLE_COMMAND: Final[str] = "--tile"
REPALCE_COMMAND: Final[str] = "--random"

SET_START: Final[str] = "{"
SET_END: Final[str] = "}"
SET_SEPARATOR: Final[str] = "|"

NEGATIVE_COMMAND: Final[str] = "--no"


class Prompt:
    original: str
    tileable: bool
    _parsed_str: str

    enable_replace: bool
    split_prompt: List[str]
    random_indices: List[int]
    random_list: List[List[str]]
    negative: str

    def get_parsed(self, *, used_prompt: str, tokenizer) -> PrasedPrompt:
        tokens = tokenizer.tokenize(used_prompt)
        used_prompt_tokens, used_prompt_truncated, = (
            tokens,
            tokens[tokenizer.model_max_length :],
        )

        pp = PrasedPrompt(
            used_prompt=used_prompt,
            used_prompt_tokens=used_prompt_tokens,
            used_prompt_truncated=used_prompt_truncated,
            negative_prompt=self.negative,
            tileable=self.tileable,
        )
        return pp

    def __init__(self, *, original: str):
        self.original = original
        self._parsed_str = self.original
        self.tileable = False
        self.enable_replace = False
        self.negative = ""

        if TILEABLE_COMMAND in self._parsed_str:
            self._parsed_str = self._parsed_str.replace(TILEABLE_COMMAND, "")
            self.tileable = True

        if NEGATIVE_COMMAND in self._parsed_str:
            _negs = []
            tmp: List[str] = self._parsed_str.split(" ")
            j = 0
            while j < len(tmp):
                if tmp[j] != NEGATIVE_COMMAND:
                    j += 1
                    continue

                del tmp[j]
                if j >= len(tmp):
                    break
                _group: bool = False
                if tmp[j].startswith(SET_START):
                    tmp[j] = tmp[j][1:]
                    _group = True

                while j < len(tmp):
                    if not _group:
                        _negs.append(tmp[j])
                        del tmp[j]
                        break
                    else:
                        if tmp[j].endswith(SET_END):
                            _negs.append(tmp[j][:-1])
                            del tmp[j]
                            break
                        else:
                            _negs.append(tmp[j])
                            del tmp[j]

            self._parsed_str = " ".join(tmp)
            self.negative = " ".join(_negs)

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
