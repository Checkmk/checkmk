#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    check_access: bool
    allow_legacy: bool
    agent_channel: tuple[Literal["mailslot"], None] | tuple[Literal["tcp"], int] | None = None


def _path_to(entry: str) -> list[str]:
    return ["system", "controller", entry]


def get_win_controller_windows_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=_path_to("check"), content=config.check_access)
    yield WindowsConfigEntry(path=_path_to("force_legacy"), content=config.allow_legacy)
    match config.agent_channel:
        case None:
            return
        case ("mailslot", _):
            yield WindowsConfigEntry(path=_path_to("agent_channel"), content="mailslot")
        case ("tcp", port):
            yield WindowsConfigEntry(path=_path_to("agent_channel"), content=f"localhost:{port}")


bakery_plugin_win_controller = BakeryPlugin(
    name="win_controller",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_win_controller_windows_config,
)
