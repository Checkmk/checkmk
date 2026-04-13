#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.lvm.bakery.lvm import bakery_plugin_lvm


def test_no_deploy() -> None:
    conf = bakery_plugin_lvm.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert not list(bakery_plugin_lvm.files_function(conf))


def test_deploy_sync() -> None:
    conf = bakery_plugin_lvm.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_lvm.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("lvm"), interval=None),
    ]


def test_deploy_cached() -> None:
    conf = bakery_plugin_lvm.parameter_parser({"deployment": ("cached", 300.0)})
    result = list(bakery_plugin_lvm.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("lvm"), interval=300),
    ]
