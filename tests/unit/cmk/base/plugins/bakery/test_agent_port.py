#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsGlobalConfigEntry
from cmk.base.plugins.bakery.agent_port import get_agent_port_windows_config


def test_agent_port_windows_config() -> None:
    result = list(get_agent_port_windows_config({"port": 6556}))
    expected = [WindowsGlobalConfigEntry(name="port", content=6556)]
    assert result == expected


def test_agent_port_windows_config_custom_port() -> None:
    result = list(get_agent_port_windows_config({"port": 12345}))
    expected = [WindowsGlobalConfigEntry(name="port", content=12345)]
    assert result == expected
