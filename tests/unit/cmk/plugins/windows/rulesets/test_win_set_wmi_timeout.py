#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_set_wmi_timeout import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(3, {"wmi_timeout": 3}, id="integer"),
        pytest.param(12, {"wmi_timeout": 12}, id="max_integer"),
        pytest.param(
            {"wmi_timeout": 5},
            {"wmi_timeout": 5},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
