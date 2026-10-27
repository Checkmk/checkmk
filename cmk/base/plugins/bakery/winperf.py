#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry, WindowsConfigGenerator


class _Counter(BaseModel):
    section: str
    counter: str


class _Config(BaseModel):
    counters: Sequence[_Counter] = ()


def get_winperf_windows_config(config: _Config) -> WindowsConfigGenerator:
    if counters := [{c.counter: c.section} for c in config.counters]:
        yield WindowsConfigEntry(path=["winperf", "counters"], content=counters)


bakery_plugin_winperf = BakeryPlugin(
    name="winperf",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_winperf_windows_config,
)
