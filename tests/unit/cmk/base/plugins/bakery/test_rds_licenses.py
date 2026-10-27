#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2 import OS, Plugin
from cmk.base.plugins.bakery.rds_licenses import bakery_plugin_rds_licenses, get_rds_licenses_files


def test_rds_licenses_files() -> None:
    assert list(
        get_rds_licenses_files(
            bakery_plugin_rds_licenses.parameter_parser({"deployment": ("sync", None)})
        )
    ) == [
        Plugin(base_os=OS.WINDOWS, source=Path("rds_licenses.ps1")),
    ]
