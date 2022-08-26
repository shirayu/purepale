#!/usr/bin/env python3

import argparse
from os import path
from pathlib import Path


def operation(path_in: Path) -> None:
    libs = []

    path_pyproject = path_in.joinpath("pyproject.toml")
    new_pyproject_lines = []
    with path_pyproject.open() as inf1:
        for line in inf1:
            if line.startswith("torch"):
                fname = Path(line.split('"')[1])
                libs.append(fname.name.split("+")[0].replace("-", "@"))
            else:
                new_pyproject_lines.append(line)
    with path_pyproject.open("w") as outf1:
        for line in new_pyproject_lines:
            outf1.write(line)

    path_lock = path_in.joinpath("poetry.lock")
    origs = []
    with path_lock.open() as inf2:
        origs = inf2.readlines()
        for idx, line in enumerate(origs):
            if idx < 5:
                continue
            if line == "[[package]]\n" and origs[idx + 1] == """name = "torch"\n""":
                end = idx + 1
                while len(origs[end].strip()) > 0:
                    end += 1
                for j in range(idx, end):
                    origs[j] = ""
            elif line == "[package.source]\n" and origs[idx + 1] == """type = "file"\n""":
                for j in range(idx, idx + 3):
                    origs[j] = ""

    with path_lock.open("w") as outf2:
        for line in origs:
            outf2.write(line)

    for lib in libs:
        print(lib)


def get_opts() -> argparse.Namespace:
    oparser = argparse.ArgumentParser()
    oparser.add_argument("--input", "-i", type=Path, default=".", required=False)
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    operation(opts.input)


if __name__ == "__main__":
    main()
