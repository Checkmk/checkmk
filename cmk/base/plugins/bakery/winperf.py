#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


def get_winperf_windows_config(conf: Sequence[tuple[str, str]]) -> WindowsConfigGenerator:
    counters = [{counterspec: section} for (section, counterspec) in conf]
    if counters:
        yield WindowsConfigEntry(path=["winperf", "counters"], content=counters)


register.bakery_plugin(
    name="winperf",
    windows_config_function=get_winperf_windows_config,
)
