#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.logins.bakery.mk_logins import bakery_plugin_mk_logins


def test_mk_logins_files_enabled() -> None:
    conf = bakery_plugin_mk_logins.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_mk_logins.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("mk_logins"), interval=None)]


def test_mk_logins_files_disabled() -> None:
    conf = bakery_plugin_mk_logins.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_mk_logins.files_function(conf)) == []
