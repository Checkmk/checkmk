#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.winperf_if import get_winperf_if_files


def test_winperf_if_files_ps1() -> None:
    result = list(get_winperf_if_files({"deployment": ("sync", None)}))
    assert result == [
        Plugin(base_os=OS.WINDOWS, source=Path("windows_if.ps1"), interval=None),
    ]


def test_winperf_if_files_bat() -> None:
    result = list(get_winperf_if_files({"deployment": ("sync", None), "use_bat_plugin": True}))
    assert result == [
        Plugin(base_os=OS.WINDOWS, source=Path("wmic_if.bat"), interval=None),
    ]


def test_winperf_if_files_do_not_deploy() -> None:
    result = list(get_winperf_if_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
