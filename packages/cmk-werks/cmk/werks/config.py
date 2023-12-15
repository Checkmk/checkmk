#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    editions: list[tuple[str, str]]
    components: list[tuple[str, str]]
    edition_components: dict[str, list[tuple[str, str]]]
    classes: list[tuple[str, str, str]]
    levels: list[tuple[str, str]]
    compatible: list[tuple[str, str]]
    online_url: str
    current_version: str

    def all_components(self) -> list[tuple[str, str]]:
        return sum(self.edition_components.values(), self.components)


def _load_current_version(defines_make: Path) -> str:
    with defines_make.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION"):
                version = line.split("=", 1)[1].strip()
                return version
    raise RuntimeError("Failed to read VERSION from defines.make")


def load_config(werk_config: Path, defines_make: Path) -> Config:
    data: dict[str, object] = {}
    exec(  # pylint: disable=exec-used # nosec B102 # BNS:aee528
        werk_config.read_text(encoding="utf-8"), data, data
    )

    data.pop("__builtins__")
    data["current_version"] = _load_current_version(defines_make)
    return Config.model_validate(data)
