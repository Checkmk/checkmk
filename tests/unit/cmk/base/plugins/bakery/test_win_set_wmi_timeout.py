#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.win_set_wmi_timeout import (
    get_win_set_wmi_timeout_windows_config,
)


def test_win_set_wmi_timeout_windows_config() -> None:
    conf = {"wmi_timeout": 30}
    result = list(get_win_set_wmi_timeout_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["global", "wmi_timeout"], content=30),
    ]


def test_win_set_wmi_timeout_windows_config_default() -> None:
    conf: dict[str, object] = {}
    result = list(get_win_set_wmi_timeout_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["global", "wmi_timeout"], content=3),
    ]
