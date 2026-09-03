#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_script_async import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param("parallel", {"mode": "parallel"}, id="string"),
        pytest.param({"mode": "sequential"}, {"mode": "sequential"}, id="already_migrated"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value",
    [pytest.param("random", id="str"), pytest.param(None, id="none"), pytest.param({}, id="empty")],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
