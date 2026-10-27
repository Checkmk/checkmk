#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigGenerator, WindowsSystemConfigEntry


class _Config(BaseModel):
    cleanup_mode: Literal["none", "smart", "all"] = "none"


def get_win_clean_uninstall_windows_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsSystemConfigEntry(name="cleanup_uninstall", content=config.cleanup_mode)


bakery_plugin_win_clean_uninstall = BakeryPlugin(
    name="win_clean_uninstall",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_win_clean_uninstall_windows_config,
)
