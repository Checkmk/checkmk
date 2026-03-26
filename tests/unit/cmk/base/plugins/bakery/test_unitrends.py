#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.unitrends import get_unitrends_files


def test_unitrends_files() -> None:
    result = sorted(get_unitrends_files({"deployment": ("sync", None)}), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("unitrends_backup"), interval=None),
            Plugin(base_os=OS.LINUX, source=Path("unitrends_replication.py"), interval=None),
        ],
        key=repr,
    )
    assert result == expected
