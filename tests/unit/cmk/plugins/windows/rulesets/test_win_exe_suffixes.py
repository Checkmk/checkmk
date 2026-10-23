#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_exe_suffixes import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"mode": ("all_files", None)}, id="execute_all"),
        pytest.param(["exe", "ps1"], {"mode": ("only", ["exe", "ps1"])}, id="list"),
        pytest.param([], {"mode": ("only", [])}, id="execute_nothing"),
        pytest.param(
            {"mode": ("only", ["exe"])}, {"mode": ("only", ["exe"])}, id="already_migrated"
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize("value", [pytest.param("exe", id="str"), pytest.param({}, id="empty")])
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
