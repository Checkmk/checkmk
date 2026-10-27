#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.base.plugins.bakery.winperf import bakery_plugin_winperf, get_winperf_windows_config


def test_winperf_windows_config_with_counters() -> None:
    conf = {
        "counters": [
            {"section": "my_section", "counter": "12345"},
            {"section": "other_section", "counter": "67890"},
        ]
    }
    assert list(get_winperf_windows_config(bakery_plugin_winperf.parameter_parser(conf))) == [
        WindowsConfigEntry(
            path=["winperf", "counters"],
            content=[{"12345": "my_section"}, {"67890": "other_section"}],
        ),
    ]


def test_winperf_windows_config_empty() -> None:
    assert (
        list(get_winperf_windows_config(bakery_plugin_winperf.parameter_parser({"counters": []})))
        == []
    )


def test_winperf_windows_config_single_counter() -> None:
    conf = {"counters": [{"section": "processor", "counter": "238"}]}
    assert list(get_winperf_windows_config(bakery_plugin_winperf.parameter_parser(conf))) == [
        WindowsConfigEntry(path=["winperf", "counters"], content=[{"238": "processor"}]),
    ]
