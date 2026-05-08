#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.smart.bakery.smart import bakery_plugin_smart


def test_smart_files_smart_posix_sync() -> None:
    conf = bakery_plugin_smart.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_smart.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("smart_posix"), interval=None),
    ]


def test_smart_files_smart_legacy_sync() -> None:
    conf = bakery_plugin_smart.parameter_parser(
        {"deployment": ("sync", None), "use_legacy_plugin": True}
    )
    result = list(bakery_plugin_smart.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("smart"), interval=None),
    ]


def test_smart_files_smart_posix_cached() -> None:
    conf = bakery_plugin_smart.parameter_parser({"deployment": ("cached", 3600.0)})
    result = list(bakery_plugin_smart.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("smart_posix"), interval=3600.0),
    ]


def test_smart_files_do_not_deploy() -> None:
    conf = bakery_plugin_smart.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_smart.files_function(conf)) == []
