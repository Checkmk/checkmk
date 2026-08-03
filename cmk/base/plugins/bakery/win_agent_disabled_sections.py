#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from .bakery_api.v1 import register, WindowsConfigGenerator, WindowsGlobalConfigEntry


def get_win_agent_disabled_sections_windows_config(conf: Any) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="disabled_sections", content=conf)


register.bakery_plugin(
    name="win_agent_disabled_sections",
    windows_config_function=get_win_agent_disabled_sections_windows_config,
)
