#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.collection.bakery.mk_zypper import bakery_plugin_mk_zypper


def test_mk_zypper_files_sync() -> None:
    conf = bakery_plugin_mk_zypper.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_mk_zypper.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("mk_zypper"), interval=None)]


def test_mk_zypper_files_cached() -> None:
    conf = bakery_plugin_mk_zypper.parameter_parser({"deployment": ("cached", 300.0)})
    result = list(bakery_plugin_mk_zypper.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("mk_zypper"), interval=300.0)]


def test_mk_zypper_files_do_not_deploy() -> None:
    conf = bakery_plugin_mk_zypper.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_mk_zypper.files_function(conf)) == []
