#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, PluginConfig


class _Config(BaseModel):
    python_version: Literal["auto", "python2", "python3"]
    command: str = ""
    """Empty string: use the default commands"""


def get_python_plugins_files(config: _Config) -> FileGenerator:
    if config.python_version == "auto" and not config.command:
        return

    for base_os in [OS.LINUX, OS.SOLARIS, OS.AIX]:
        yield PluginConfig(
            base_os=base_os,
            lines=list(_get_python_plugins_config(config)),
            target=Path("python_path.cfg"),
            include_header=True,
        )


def _get_python_plugins_config(config: _Config) -> Iterator[str]:
    if config.command and config.python_version in ("python2", "auto"):
        yield f"PYTHON2={quote(config.command)}"

    if config.command and config.python_version in ("python3", "auto"):
        yield f"PYTHON3={quote(config.command)}"

    if config.python_version == "python2":
        yield "PYTHON3="

    if config.python_version == "python3":
        yield "PYTHON2="


bakery_plugin_python_plugins = BakeryPlugin(
    name="python_plugins",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_python_plugins_files,
)
