#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    wmi_timeout: int = 3


def get_win_set_wmi_timeout_windows_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=["global", "wmi_timeout"], content=config.wmi_timeout)


bakery_plugin_win_set_wmi_timeout = BakeryPlugin(
    name="win_set_wmi_timeout",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_win_set_wmi_timeout_windows_config,
)
