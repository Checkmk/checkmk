#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigGenerator, WindowsGlobalConfigEntry


class _Config(BaseModel):
    mode: tuple[Literal["all_files"], None] | tuple[Literal["only"], Sequence[str]]


def get_win_exe_suffixes_windows_config(config: _Config) -> WindowsConfigGenerator:
    match config.mode:
        case ("all_files", _):
            return
        case ("only", suffixes):
            yield WindowsGlobalConfigEntry(name="execute", content=list(suffixes))


bakery_plugin_win_exe_suffixes = BakeryPlugin(
    name="win_exe_suffixes",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_win_exe_suffixes_windows_config,
)
