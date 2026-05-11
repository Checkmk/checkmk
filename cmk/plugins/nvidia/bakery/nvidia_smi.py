#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, OS, Plugin, PluginConfig


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    nvidia_smi_path: str | None = None


def get_nvidia_smi_files(conf: _Config) -> Iterable[Plugin | PluginConfig]:
    if conf.deployment[0] == "do_not_deploy":
        return

    interval = conf.deployment[1]
    yield Plugin(base_os=OS.LINUX, source=Path("nvidia_smi"), interval=interval)
    yield Plugin(base_os=OS.WINDOWS, source=Path("nvidia_smi.ps1"), interval=interval)
    if conf.nvidia_smi_path is not None:
        yield PluginConfig(
            base_os=OS.WINDOWS,
            lines=[f"$nvidia_smi_path = '{conf.nvidia_smi_path}'"],
            target=Path("nvidia_smi_cfg.ps1"),
            include_header=True,
        )


bakery_plugin_nvidia_smi = BakeryPlugin(
    name="nvidia_smi",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_nvidia_smi_files,
)
