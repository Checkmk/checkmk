#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.winperf import get_winperf_windows_config


def test_winperf_windows_config_with_counters() -> None:
    conf = [
        ("my_section", "12345"),
        ("other_section", "67890"),
    ]
    assert list(get_winperf_windows_config(conf)) == [
        WindowsConfigEntry(
            path=["winperf", "counters"],
            content=[{"12345": "my_section"}, {"67890": "other_section"}],
        ),
    ]


def test_winperf_windows_config_empty() -> None:
    assert list(get_winperf_windows_config([])) == []


def test_winperf_windows_config_single_counter() -> None:
    assert list(get_winperf_windows_config([("processor", "238")])) == [
        WindowsConfigEntry(
            path=["winperf", "counters"],
            content=[{"238": "processor"}],
        ),
    ]
