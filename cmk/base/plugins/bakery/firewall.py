#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import (
    register,
    WindowsConfigEntry,
    WindowsConfigGenerator,
)


class _Config(BaseModel):
    mode: Literal["none", "remove", "configure"]
    port: Literal["auto", "all"]


def get_firewall_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(path=["system", "firewall", "mode"], content=config.mode)
    yield WindowsConfigEntry(path=["system", "firewall", "port"], content=config.port)


register.bakery_plugin(
    name="firewall",
    windows_config_function=get_firewall_windows_config,
)
