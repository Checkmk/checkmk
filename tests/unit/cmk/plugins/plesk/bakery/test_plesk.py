#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.plesk.bakery.plesk import bakery_plugin_plesk


def test_do_not_deploy() -> None:
    conf = bakery_plugin_plesk.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert not list(bakery_plugin_plesk.files_function(conf))


def test_plesk_files() -> None:
    conf = bakery_plugin_plesk.parameter_parser({"deployment": ("cached", 3600.0)})
    result = sorted(bakery_plugin_plesk.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("plesk_backups.py"), interval=3600),
            Plugin(base_os=OS.LINUX, source=Path("plesk_domains.py")),
        ],
        key=repr,
    )
    assert result == expected
