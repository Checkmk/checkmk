#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    nvidia_smi_path: str | None = None


def get_nvidia_smi_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    yield Plugin(base_os=OS.LINUX, source=Path("nvidia_smi"), interval=interval)
    yield Plugin(base_os=OS.WINDOWS, source=Path("nvidia_smi.ps1"), interval=interval)
    if config.nvidia_smi_path is not None:
        yield PluginConfig(
            base_os=OS.WINDOWS,
            lines=[f"$nvidia_smi_path = '{config.nvidia_smi_path}'"],
            target=Path("nvidia_smi_cfg.ps1"),
            include_header=True,
        )


register.bakery_plugin(
    name="nvidia_smi",
    files_function=get_nvidia_smi_files,
)
