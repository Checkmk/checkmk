#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    restart_on_crash: Literal["yes", "no"]
    error_mode: Literal["log", "ignore"]
    start_mode: Literal["auto", "delayed", "demand", "disabled"]


def get_win_service_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(
        path=["system", "service", "restart_on_crash"], content=config.restart_on_crash
    )
    yield WindowsConfigEntry(path=["system", "service", "error_mode"], content=config.error_mode)
    yield WindowsConfigEntry(path=["system", "service", "start_mode"], content=config.start_mode)


register.bakery_plugin(
    name="win_service",
    windows_config_function=get_win_service_windows_config,
)
