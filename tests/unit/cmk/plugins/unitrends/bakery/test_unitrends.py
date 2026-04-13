#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.unitrends.bakery.unitrends import bakery_plugin_unitrends


def test_no_deploy() -> None:
    conf = bakery_plugin_unitrends.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert not list(bakery_plugin_unitrends.files_function(conf))


def test_deploy_sync() -> None:
    conf = bakery_plugin_unitrends.parameter_parser({"deployment": ("sync", None)})
    result = sorted(bakery_plugin_unitrends.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("unitrends_backup"), interval=None),
            Plugin(base_os=OS.LINUX, source=Path("unitrends_replication.py"), interval=None),
        ],
        key=repr,
    )
    assert result == expected


def test_deploy_cached() -> None:
    conf = bakery_plugin_unitrends.parameter_parser({"deployment": ("cached", 300.0)})
    result = sorted(bakery_plugin_unitrends.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("unitrends_backup"), interval=300),
            Plugin(base_os=OS.LINUX, source=Path("unitrends_replication.py"), interval=300),
        ],
        key=repr,
    )
    assert result == expected
