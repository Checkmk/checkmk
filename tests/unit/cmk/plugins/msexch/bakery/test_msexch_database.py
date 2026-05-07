#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin
from cmk.plugins.msexch.bakery.msexch_database import bakery_plugin_msexch_database


@pytest.mark.parametrize(
    "conf, expected_files",
    [
        (
            {"deployment": ("sync", None)},
            [Plugin(base_os=OS.WINDOWS, source=Path("msexch_database.ps1"), interval=None)],
        ),
        (
            {"deployment": ("cached", 3600.0)},
            [Plugin(base_os=OS.WINDOWS, source=Path("msexch_database.ps1"), interval=3600.0)],
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            [],
        ),
    ],
)
def test_msexch_database_files(
    conf: dict[str, object],
    expected_files: list[Plugin],
) -> None:
    parsed = bakery_plugin_msexch_database.parameter_parser(conf)
    result = list(bakery_plugin_msexch_database.files_function(parsed))
    assert result == expected_files
