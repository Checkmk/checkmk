#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, PluginConfig
from cmk.base.plugins.bakery.runas import get_runas_files


def test_runas_files() -> None:
    conf = [
        [("plugin", "myuser", "/usr/lib/check_mk_agent/plugins/my_plugin")],
        [("local", "", "/usr/lib/check_mk_agent/local/my_local")],
    ]
    result = list(get_runas_files(conf))
    expected = [
        PluginConfig(
            base_os=OS.LINUX,
            lines=[
                "plugin   myuser           /usr/lib/check_mk_agent/plugins/my_plugin",
                "local    -                /usr/lib/check_mk_agent/local/my_local",
            ],
            target=Path("runas.cfg"),
            include_header=True,
        ),
    ]
    assert result == expected


def test_runas_files_empty() -> None:
    result = list(get_runas_files([]))
    expected = [
        PluginConfig(
            base_os=OS.LINUX,
            lines=[],
            target=Path("runas.cfg"),
            include_header=True,
        ),
    ]
    assert result == expected
