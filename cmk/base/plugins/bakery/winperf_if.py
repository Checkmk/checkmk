#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, FileGenerator, OS, Plugin


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    use_bat_plugin: bool = False


def get_winperf_if_files(config: _Config) -> FileGenerator:
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    source = Path("wmic_if.bat") if config.use_bat_plugin else Path("windows_if.ps1")
    yield Plugin(base_os=OS.WINDOWS, source=source, interval=interval)


bakery_plugin_winperf_if = BakeryPlugin(
    name="winperf_if",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    files_function=get_winperf_if_files,
)
