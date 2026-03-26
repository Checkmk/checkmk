#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.netstat import get_netstat_files


def test_netstat_files_with_interval() -> None:
    conf = {"deployment": ("cached", 120.0)}
    result = sorted(get_netstat_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(
                base_os=OS.LINUX,
                source=Path("netstat.linux"),
                target=Path("netstat"),
                interval=120,
            ),
            Plugin(
                base_os=OS.AIX,
                source=Path("netstat.aix"),
                target=Path("netstat"),
                interval=120,
            ),
            Plugin(
                base_os=OS.WINDOWS,
                source=Path("netstat_an.bat"),
                interval=120,
                asynchronous=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_netstat_files_without_interval() -> None:
    conf = {"deployment": ("sync", None)}
    result = sorted(get_netstat_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(
                base_os=OS.LINUX,
                source=Path("netstat.linux"),
                target=Path("netstat"),
            ),
            Plugin(
                base_os=OS.AIX,
                source=Path("netstat.aix"),
                target=Path("netstat"),
            ),
            Plugin(
                base_os=OS.WINDOWS,
                source=Path("netstat_an.bat"),
                asynchronous=True,
            ),
        ],
        key=repr,
    )
    assert result == expected
