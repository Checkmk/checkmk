#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.db2.bakery.db2_mem import bakery_plugin_db2_mem


def test_db2_mem_deploy() -> None:
    conf = bakery_plugin_db2_mem.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_db2_mem.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("db2_mem"), interval=None),
        Plugin(base_os=OS.SOLARIS, source=Path("db2_mem"), interval=None),
        Plugin(base_os=OS.AIX, source=Path("db2_mem"), interval=None),
    ]


def test_db2_mem_deploy_with_interval() -> None:
    conf = bakery_plugin_db2_mem.parameter_parser({"deployment": ("cached", 300.0)})
    result = list(bakery_plugin_db2_mem.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("db2_mem"), interval=300.0),
        Plugin(base_os=OS.SOLARIS, source=Path("db2_mem"), interval=300.0),
        Plugin(base_os=OS.AIX, source=Path("db2_mem"), interval=300.0),
    ]


def test_db2_mem_do_not_deploy() -> None:
    conf = bakery_plugin_db2_mem.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_db2_mem.files_function(conf)) == []
