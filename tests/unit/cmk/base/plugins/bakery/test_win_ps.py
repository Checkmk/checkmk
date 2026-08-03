#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.win_ps import get_win_ps_windows_config


def test_win_ps_no_wmi() -> None:
    conf: Mapping[str, bool] = {}
    result = list(get_win_ps_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["ps", "use_wmi"], content=False),
    ]


def test_win_ps_use_wmi_false() -> None:
    conf = {"use_wmi": False}
    result = list(get_win_ps_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["ps", "use_wmi"], content=False),
    ]


def test_win_ps_use_wmi_true_no_full_path() -> None:
    conf = {"use_wmi": True}
    result = list(get_win_ps_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["ps", "use_wmi"], content=True),
    ]


def test_win_ps_use_wmi_true_with_full_path() -> None:
    conf = {"use_wmi": True, "full_path": True}
    result = list(get_win_ps_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["ps", "use_wmi"], content=True),
        WindowsConfigEntry(path=["ps", "full_path"], content=True),
    ]


def test_win_ps_use_wmi_true_full_path_false() -> None:
    conf = {"use_wmi": True, "full_path": False}
    result = list(get_win_ps_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["ps", "use_wmi"], content=True),
    ]
