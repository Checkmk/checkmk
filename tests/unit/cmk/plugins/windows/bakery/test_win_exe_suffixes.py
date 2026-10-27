#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v2 import WindowsGlobalConfigEntry
from cmk.plugins.windows.bakery.win_exe_suffixes import (
    bakery_plugin_win_exe_suffixes,
    get_win_exe_suffixes_windows_config,
)


def test_win_exe_suffixes_windows_config() -> None:
    assert list(
        get_win_exe_suffixes_windows_config(
            bakery_plugin_win_exe_suffixes.parameter_parser(
                {"mode": ("only", ["exe", "bat", "vbs"])}
            )
        )
    ) == [
        WindowsGlobalConfigEntry(name="execute", content=["exe", "bat", "vbs"]),
    ]


def test_win_exe_suffixes_windows_config_empty_list() -> None:
    assert list(
        get_win_exe_suffixes_windows_config(
            bakery_plugin_win_exe_suffixes.parameter_parser({"mode": ("only", [])})
        )
    ) == [
        WindowsGlobalConfigEntry(name="execute", content=[]),
    ]


def test_win_exe_suffixes_windows_config_execute_all() -> None:
    assert (
        list(
            get_win_exe_suffixes_windows_config(
                bakery_plugin_win_exe_suffixes.parameter_parser({"mode": ("all_files", None)})
            )
        )
        == []
    )
