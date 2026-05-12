#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsSystemConfigEntry
from cmk.base.plugins.bakery.win_clean_uninstall import (
    get_win_clean_uninstall_windows_config,
)


def test_win_clean_uninstall_windows_config_none() -> None:
    result = list(get_win_clean_uninstall_windows_config({"cleanup_mode": "none"}))
    assert result == [WindowsSystemConfigEntry(name="cleanup_uninstall", content="none")]


def test_win_clean_uninstall_windows_config_smart() -> None:
    result = list(get_win_clean_uninstall_windows_config({"cleanup_mode": "smart"}))
    assert result == [WindowsSystemConfigEntry(name="cleanup_uninstall", content="smart")]


def test_win_clean_uninstall_windows_config_all() -> None:
    result = list(get_win_clean_uninstall_windows_config({"cleanup_mode": "all"}))
    assert result == [WindowsSystemConfigEntry(name="cleanup_uninstall", content="all")]
