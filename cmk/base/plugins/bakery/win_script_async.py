#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from .bakery_api.v1 import register, WindowsConfigGenerator, WindowsGlobalConfigEntry


def get_win_script_async_windows_config(
    conf: Literal["sequential", "parallel"],
) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="async_script_execution", content=conf)


register.bakery_plugin(
    name="win_script_async",
    windows_config_function=get_win_script_async_windows_config,
)
