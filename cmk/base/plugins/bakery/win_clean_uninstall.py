#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigGenerator, WindowsSystemConfigEntry


class _Config(BaseModel):
    cleanup_mode: Literal["none", "smart", "all"] = "none"


def get_win_clean_uninstall_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsSystemConfigEntry(name="cleanup_uninstall", content=config.cleanup_mode)


register.bakery_plugin(
    name="win_clean_uninstall",
    windows_config_function=get_win_clean_uninstall_windows_config,
)
