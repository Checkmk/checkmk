#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.install_python import get_agent_install_python_config


def test_install_python_config_system() -> None:
    conf = {"usage": "system"}
    result = list(get_agent_install_python_config(conf))
    expected = [WindowsConfigEntry(path=["modules", "python"], content="system")]
    assert result == expected


def test_install_python_config_auto() -> None:
    conf = {"usage": "auto"}
    result = list(get_agent_install_python_config(conf))
    expected = [WindowsConfigEntry(path=["modules", "python"], content="auto")]
    assert result == expected
