#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigGenerator, WindowsGlobalConfigEntry


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]


def get_remove_legacy_windows_config(config: _Config) -> WindowsConfigGenerator:
    if config.deployment[0] == "do_not_deploy":
        return
    yield WindowsGlobalConfigEntry(name="remove_legacy", content="yes")


bakery_plugin_remove_legacy = BakeryPlugin(
    name="remove_legacy",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_remove_legacy_windows_config,
)
