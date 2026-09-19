#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.bakery.v1 import WindowsGlobalConfigEntry
from cmk.base.plugins.bakery.win_script_async import get_win_script_async_windows_config


@pytest.mark.parametrize("mode", ["parallel", "sequential"])
def test_win_script_async_windows_config(mode: str) -> None:
    assert list(get_win_script_async_windows_config(mode)) == [
        WindowsGlobalConfigEntry(name="async_script_execution", content=mode),
    ]
