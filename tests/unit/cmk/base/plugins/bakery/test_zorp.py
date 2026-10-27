#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2 import OS, Plugin
from cmk.base.plugins.bakery.zorp import bakery_plugin_zorp, get_zorp_files


def test_zorp_files_do_not_deploy() -> None:
    conf = {"deployment": ("do_not_deploy", None)}
    result = list(get_zorp_files(bakery_plugin_zorp.parameter_parser(conf)))
    assert result == []


def test_zorp_files_sync() -> None:
    conf = {"deployment": ("sync", None)}
    result = list(get_zorp_files(bakery_plugin_zorp.parameter_parser(conf)))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("zorp")),
    ]
    assert result == expected


def test_zorp_files_cached() -> None:
    conf = {"deployment": ("cached", 300.0)}
    result = list(get_zorp_files(bakery_plugin_zorp.parameter_parser(conf)))
    expected = [
        Plugin(base_os=OS.LINUX, source=Path("zorp"), interval=300),
    ]
    assert result == expected
