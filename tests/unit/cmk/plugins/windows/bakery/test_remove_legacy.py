#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bakery.v2 import WindowsGlobalConfigEntry
from cmk.plugins.windows.bakery.remove_legacy import (
    bakery_plugin_remove_legacy,
    get_remove_legacy_windows_config,
)

CONFIG_DEPLOY = {"deployment": ("sync", None)}
CONFIG_NO_DEPLOY = {"deployment": ("do_not_deploy", None)}


def test_remove_legacy_windows_config_enabled() -> None:
    result = list(
        get_remove_legacy_windows_config(
            bakery_plugin_remove_legacy.parameter_parser(CONFIG_DEPLOY)
        )
    )
    expected = [
        WindowsGlobalConfigEntry(name="remove_legacy", content="yes"),
    ]
    assert result == expected


def test_remove_legacy_windows_config_disabled() -> None:
    result = list(
        get_remove_legacy_windows_config(
            bakery_plugin_remove_legacy.parameter_parser(CONFIG_NO_DEPLOY)
        )
    )
    assert result == []
