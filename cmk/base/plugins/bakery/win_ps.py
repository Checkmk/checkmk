#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    use_wmi: bool = False
    full_path: bool = False


def get_win_ps_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(path=["ps", "use_wmi"], content=config.use_wmi)

    if config.use_wmi and config.full_path:
        yield WindowsConfigEntry(path=["ps", "full_path"], content=True)


register.bakery_plugin(
    name="win_ps",
    windows_config_function=get_win_ps_windows_config,
)
