#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry, WindowsConfigGenerator


def _path_to(entry: str) -> list[str]:
    return ["system", "controller", entry]


class _Config(BaseModel):
    agent_ctl_enabled: tuple[Literal["enabled", "disabled"], Mapping[str, bool] | None] = (
        "enabled",
        {},
    )


def get_agent_controller_windows_config(config: _Config) -> WindowsConfigGenerator:
    choice, runtime_opts = config.agent_ctl_enabled
    yield WindowsConfigEntry(path=_path_to("run"), content=choice == "enabled")
    if choice == "enabled" and runtime_opts:
        yield from (
            WindowsConfigEntry(path=_path_to(runtime_opt), content=value)
            for runtime_opt, value in runtime_opts.items()
        )


bakery_plugin_agent_controller = BakeryPlugin(
    name="agent_controller",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_agent_controller_windows_config,
)
