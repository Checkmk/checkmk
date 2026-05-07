#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.collection.bakery.kaspersky_av import bakery_plugin_kaspersky_av


def test_kaspersky_av_files_enabled() -> None:
    conf = bakery_plugin_kaspersky_av.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_kaspersky_av.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("kaspersky_av"), interval=None)]


def test_kaspersky_av_files_disabled() -> None:
    conf = bakery_plugin_kaspersky_av.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_kaspersky_av.files_function(conf)) == []
