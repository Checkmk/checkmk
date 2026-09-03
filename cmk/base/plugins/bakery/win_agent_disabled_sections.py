#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigGenerator, WindowsGlobalConfigEntry


class _Config(BaseModel):
    sections: Sequence[str]


def get_win_agent_disabled_sections_windows_config(
    conf: Mapping[str, object],
) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsGlobalConfigEntry(name="disabled_sections", content=list(config.sections))


register.bakery_plugin(
    name="win_agent_disabled_sections",
    windows_config_function=get_win_agent_disabled_sections_windows_config,
)
