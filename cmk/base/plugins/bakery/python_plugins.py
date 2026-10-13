#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, PluginConfig, register


class _Config(BaseModel):
    version: Literal["auto", "python2", "python3"]
    command: str = ""
    """Empty string: use the default commands"""


def get_python_plugins_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.version == "auto" and not config.command:
        return

    for base_os in [OS.LINUX, OS.SOLARIS, OS.AIX]:
        yield PluginConfig(
            base_os=base_os,
            lines=list(_get_python_plugins_config(config)),
            target=Path("python_path.cfg"),
            include_header=True,
        )


def _get_python_plugins_config(config: _Config) -> Iterator[str]:
    if config.command and config.version in ("python2", "auto"):
        yield f"PYTHON2={quote(config.command)}"

    if config.command and config.version in ("python3", "auto"):
        yield f"PYTHON3={quote(config.command)}"

    if config.version == "python2":
        yield "PYTHON3="

    if config.version == "python3":
        yield "PYTHON2="


register.bakery_plugin(
    name="python_plugins",
    files_function=get_python_plugins_files,
)
