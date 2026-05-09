#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigGenerator, WindowsGlobalConfigEntry


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]


def get_remove_legacy_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return
    yield WindowsGlobalConfigEntry(name="remove_legacy", content="yes")


register.bakery_plugin(
    name="remove_legacy",
    windows_config_function=get_remove_legacy_windows_config,
)
