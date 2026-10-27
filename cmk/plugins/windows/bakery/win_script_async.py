#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigGenerator, WindowsGlobalConfigEntry


class _Config(BaseModel):
    mode: Literal["sequential", "parallel"]


def get_win_script_async_windows_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="async_script_execution", content=config.mode)


bakery_plugin_win_script_async = BakeryPlugin(
    name="win_script_async",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_win_script_async_windows_config,
)
