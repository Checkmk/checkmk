#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.windows_multipath import get_windows_multipath_files


def test_windows_multipath_files_enabled() -> None:
    result = list(get_windows_multipath_files({"deployment": ("sync", None)}))
    assert result == [
        Plugin(base_os=OS.WINDOWS, source=Path("windows_multipath.ps1"), interval=None),
    ]


def test_windows_multipath_files_disabled() -> None:
    result = list(get_windows_multipath_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
