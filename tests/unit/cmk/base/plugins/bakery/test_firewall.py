#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.firewall import get_firewall_windows_config


def test_firewall_windows_config() -> None:
    conf = {"mode": "configure", "port": "auto"}
    result = list(get_firewall_windows_config(conf))
    expected = [
        WindowsConfigEntry(path=["system", "firewall", "mode"], content="configure"),
        WindowsConfigEntry(path=["system", "firewall", "port"], content="auto"),
    ]
    assert result == expected
