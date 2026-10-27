#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsGlobalConfigEntry
from cmk.base.plugins.bakery.only_from import get_only_from_windows_config


def test_only_from_windows_config() -> None:
    result = list(
        get_only_from_windows_config({"allowed_addresses": ["192.168.1.0/24", "10.0.0.1"]})
    )
    expected = [
        WindowsGlobalConfigEntry(name="only_from", content=["192.168.1.0/24", "10.0.0.1"]),
    ]
    assert result == expected
