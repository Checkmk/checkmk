#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    check_controller_access: bool = True
    force_legacy: bool = False
    agent_channel: tuple[Literal["mailslot"], None] | tuple[Literal["tcp"], int] | None = None


def _path_to(entry: str) -> list[str]:
    return ["system", "controller", entry]


def get_win_controller_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(path=_path_to("check"), content=config.check_controller_access)
    yield WindowsConfigEntry(path=_path_to("force_legacy"), content=config.force_legacy)
    match config.agent_channel:
        case None:
            return
        case ("mailslot", _):
            yield WindowsConfigEntry(path=_path_to("agent_channel"), content="mailslot")
        case ("tcp", port):
            yield WindowsConfigEntry(path=_path_to("agent_channel"), content=f"localhost:{port}")


register.bakery_plugin(
    name="win_controller",
    windows_config_function=get_win_controller_windows_config,
)
