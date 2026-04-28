#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin
from cmk.base.plugins.bakery.iis_app_pool_state import get_iis_app_pool_state_files


def test_iis_app_pool_state_files_enabled() -> None:
    result = list(get_iis_app_pool_state_files({"deployment": ("sync", None)}))
    expected = [Plugin(base_os=OS.WINDOWS, source=Path("iis_app_pool_state.ps1"), interval=None)]
    assert result == expected


def test_iis_app_pool_state_files_disabled() -> None:
    result = list(get_iis_app_pool_state_files({"deployment": ("do_not_deploy", None)}))
    assert result == []
