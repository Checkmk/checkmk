#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.plugins.windows.bakery.firewall import bakery_plugin_firewall, get_firewall_windows_config


@pytest.mark.parametrize(
    "mode, port",
    [
        ("configure", "auto"),
        ("remove", "auto"),
        ("none", "auto"),
        ("configure", "all"),
    ],
)
def test_firewall_windows_config(mode: str, port: str) -> None:
    conf = {"mode": mode, "port": port}
    result = list(get_firewall_windows_config(bakery_plugin_firewall.parameter_parser(conf)))
    expected = [
        WindowsConfigEntry(path=["system", "firewall", "mode"], content=mode),
        WindowsConfigEntry(path=["system", "firewall", "port"], content=port),
    ]
    assert result == expected
