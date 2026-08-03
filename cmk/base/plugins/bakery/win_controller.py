#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


def _path_to(entry: str) -> list[str]:
    return ["system", "controller", entry]


def get_win_controller_windows_config(conf: dict[str, Any]) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(
        path=_path_to("check"), content=conf.get("check_controller_access", True)
    )
    yield WindowsConfigEntry(path=_path_to("force_legacy"), content=conf.get("force_legacy", False))
    if (channel_conf := conf.get("agent_channel")) is not None:
        kind, value = channel_conf
        channel_str = "mailslot" if kind == "mailslot" else f"localhost:{value}"
        yield WindowsConfigEntry(path=_path_to("agent_channel"), content=channel_str)


register.bakery_plugin(
    name="win_controller",
    windows_config_function=get_win_controller_windows_config,
)
