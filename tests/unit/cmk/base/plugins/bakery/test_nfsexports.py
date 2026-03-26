#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.nfsexports import get_nfsexports_files


def test_nfsexports_files() -> None:
    result = sorted(get_nfsexports_files({"deployment": ("sync", None)}), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("nfsexports"), interval=None),
            Plugin(
                base_os=OS.SOLARIS,
                source=Path("nfsexports.solaris"),
                target=Path("nfsexports"),
                interval=None,
            ),
        ],
        key=repr,
    )
    assert result == expected
