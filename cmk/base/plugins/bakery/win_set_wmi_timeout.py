#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from pydantic import BaseModel

from .bakery_api.v1 import (
    register,
    WindowsConfigEntry,
    WindowsConfigGenerator,
)


class _Config(BaseModel):
    wmi_timeout: int = 3


def get_win_set_wmi_timeout_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(path=["global", "wmi_timeout"], content=config.wmi_timeout)


register.bakery_plugin(
    name="win_set_wmi_timeout",
    windows_config_function=get_win_set_wmi_timeout_windows_config,
)
