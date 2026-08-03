#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from .bakery_api.v1 import (
    register,
    WindowsConfigContent,
    WindowsConfigEntry,
    WindowsConfigGenerator,
)


def get_win_service_windows_config(
    conf: Mapping[str, WindowsConfigContent],
) -> WindowsConfigGenerator:
    for key in ["restart_on_crash", "error_mode", "start_mode"]:
        if key in conf:
            yield WindowsConfigEntry(path=["system", "service", key], content=conf[key])


register.bakery_plugin(
    name="win_service",
    windows_config_function=get_win_service_windows_config,
)
