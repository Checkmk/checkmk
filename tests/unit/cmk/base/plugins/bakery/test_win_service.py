#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.win_service import get_win_service_windows_config


def test_win_service_all_keys() -> None:
    conf = {
        "restart_on_crash": "yes",
        "error_mode": "normal",
        "start_mode": "auto",
    }
    result = list(get_win_service_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["system", "service", "restart_on_crash"], content="yes"),
        WindowsConfigEntry(path=["system", "service", "error_mode"], content="normal"),
        WindowsConfigEntry(path=["system", "service", "start_mode"], content="auto"),
    ]


def test_win_service_partial_keys() -> None:
    conf = {"restart_on_crash": "no"}
    result = list(get_win_service_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["system", "service", "restart_on_crash"], content="no"),
    ]


def test_win_service_empty_config() -> None:
    result = list(get_win_service_windows_config({}))
    assert result == []


def test_win_service_unknown_keys_ignored() -> None:
    conf = {"unknown_key": "value"}
    result = list(get_win_service_windows_config(conf))
    assert result == []
