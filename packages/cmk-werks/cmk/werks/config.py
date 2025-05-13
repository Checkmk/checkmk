#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator, ValidationInfo


class Config(BaseModel):
    editions: list[tuple[str, str]]
    components: list[tuple[str, str]]
    edition_components: dict[str, list[tuple[str, str]]]
    classes: list[tuple[str, str, str]]
    levels: list[tuple[str, str]]
    compatible: list[tuple[str, str]]
    online_url: str
    project: Literal["cmk", "cloudmk", "cma"]
    branch: str
    repo: str
    create_commit: bool = True
    """
    Should the werk tool automatically create a commit when reserving ids or creating a werk?
    This option was introduced for cloudmk, they have special requirements for commit messages.
    """
    current_version: str

    def all_components(self) -> list[tuple[str, str]]:
        return sum(self.edition_components.values(), self.components)

    @model_validator(mode="before")
    @classmethod
    def default_current_version_from_context(
        cls, data: dict[str, object], info: ValidationInfo
    ) -> dict[str, object]:
        """
        Use the 'current_version' specified via context if it is missing from the model data.
        """
        if "current_version" in data:
            return data

        if (
            info.context is not None
            and (context_version := info.context.get("current_version")) is not None
        ):
            return data | {"current_version": context_version}

        raise ValueError("current_version must be provided either directly or via context")


def try_load_current_version_from_defines_make(defines_make: Path) -> str | None:
    try:
        with defines_make.open(encoding="utf-8") as f:
            for line in f:
                if line.startswith("VERSION"):
                    version = line.split("=", 1)[1].strip()
                    return version
    except FileNotFoundError:
        pass

    return None


def load_config(werk_config: Path, *, current_version: str | None = None) -> Config:
    data: dict[str, object] = {}
    exec(werk_config.read_text(encoding="utf-8"), data, data)  # nosec B102 # BNS:aee528

    data.pop("__builtins__")
    return Config.model_validate(
        data,
        context={"current_version": current_version},
    )
