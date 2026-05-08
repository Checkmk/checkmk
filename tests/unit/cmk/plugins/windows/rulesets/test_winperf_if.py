#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.winperf_if import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            "ps1", {"deployment": ("sync", None), "use_bat_plugin": False}, id="deploy_ps1"
        ),
        pytest.param(
            "bat",
            {"deployment": ("sync", None), "use_bat_plugin": True},
            id="deploy_bat",
        ),
        pytest.param(False, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
            id="already_migrated",
        ),
        pytest.param(
            {"deployment": ("sync", None), "use_bat_plugin": True},
            {"deployment": ("sync", None), "use_bat_plugin": True},
            id="already_migrated_bat",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
