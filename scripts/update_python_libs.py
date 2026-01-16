#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This script checks the deps before and after running `make relock_venv` and writes the diff to a
file to be then picked up as git commit message."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Self

Hash = str


@dataclass(frozen=True, order=True)
class Info:
    name: str
    version: str
    hashes: list[str]


class RequriementsTxtParser:
    def __init__(self) -> None:
        self.continuing = False
        self.info: dict[str, Info] = {}

    @classmethod
    def parse(cls, path: Path) -> Self:
        parser = cls()
        with path.open() as rfile:
            parser.parse_file(rfile)
        return parser

    def parse_file(self, requirements_file: IO[str]) -> None:
        while line := requirements_file.readline():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.strip().startswith("--"):
                assert line.strip().startswith("--index-url")
                continue

            # e.g. pyjwt[crypto], bandit[sarif, toml]
            stripped_line = re.sub(r"\[[^\\]+\]", "", line.strip())
            name_version = stripped_line.replace(" @ git+", "==git+").split(maxsplit=1)[0]
            name, version = name_version.split("==", 1)
            info = Info(
                name=name,
                version=version,
                hashes=[],
            )

            while line.rstrip().endswith("\\"):
                line = requirements_file.readline()
                info.hashes.append(self._parse_continuing_line(line))
            self.info[info.name] = info

    @staticmethod
    def _parse_continuing_line(line: str) -> Hash:
        assert line.strip().startswith("--hash=sha256:")
        return line.strip().removeprefix("--hash=sha256:").removesuffix("\\").strip()


def _diff(before: dict[str, Info], after: dict[str, Info]) -> str:
    deleted = before.keys() - after.keys()
    added = after.keys() - before.keys()
    updated = {(v.name, v.version) for v in after.values() if v.name not in added} - {
        (v.name, v.version) for v in before.values()
    }
    return_value = ""
    if deleted:
        return_value = "\n".join(f"{d} removed" for d in sorted(deleted)) + "\n\n"

    # no updates seems unreasonable
    for lib, to_version in sorted(updated):
        before_version = before[lib].version
        return_value += f"{lib} updated from {before_version} to {to_version}\n"
    return_value += "\n"

    if added:
        return_value += "\n".join(
            f"{added_dep.name} {added_dep.version} added"
            for added_dep in sorted(a for a in after.values() if a.name in added)
        )
    return return_value


def test_diff() -> None:
    assert (
        _diff(
            {"a": Info("a", "1.0", []), "b": Info("b", "1.0", []), "c": Info("c", "1.0", [])},
            {"a": Info("a", "1.0", []), "c": Info("c", "2.0", []), "d": Info("d", "1.0", [])},
        )
        == "b removed\n\n"
        "c updated from 1.0 to 2.0\n\n"
        "d 1.0 added"
    )


def _main() -> None:
    requirements_txt_path = Path("requirements.txt")
    before = RequriementsTxtParser.parse(requirements_txt_path)
    requirements_txt_path.write_text("")
    subprocess.check_call(["bazel", "run", "//:lock_python_requirements"])
    after = RequriementsTxtParser.parse(requirements_txt_path)
    # there is also a omd/requirements_lock.txt file, it looks like it will vanish soon
    # I'm not sure how we would want to update that anyways. Special commit or all in one?
    # Therefore let's keep it simple for now.
    # Relocking would work like this:
    # echo > omd/requirements_lock.txt; bazel run //omd:requirements_lock
    with open(".git-commit-msg", "w") as f:
        f.write("Update Python libraries\n\n")
        f.write(_diff(before.info, after.info))
    print("git commit -F .git-commit-msg")


if __name__ == "__main__":
    _main()
