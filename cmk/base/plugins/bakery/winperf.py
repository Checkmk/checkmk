#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


class _Counter(BaseModel):
    section: str
    counter: str


class _Config(BaseModel):
    counters: Sequence[_Counter] = ()


def get_winperf_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    if counters := [{c.counter: c.section} for c in config.counters]:
        yield WindowsConfigEntry(path=["winperf", "counters"], content=counters)


register.bakery_plugin(
    name="winperf",
    windows_config_function=get_winperf_windows_config,
)
