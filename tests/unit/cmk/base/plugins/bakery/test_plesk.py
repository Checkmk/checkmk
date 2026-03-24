#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.plesk import get_plesk_files


def test_plesk_files() -> None:
    result = sorted(get_plesk_files({"deployment": ("cached", 3600.0)}), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("plesk_backups.py"), interval=3600),
            Plugin(base_os=OS.LINUX, source=Path("plesk_domains.py")),
        ],
        key=repr,
    )
    assert result == expected
