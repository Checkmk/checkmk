#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_clean_uninstall import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param("none", {"cleanup_mode": "none"}, id="none_string"),
        pytest.param("smart", {"cleanup_mode": "smart"}, id="smart_string"),
        pytest.param("all", {"cleanup_mode": "all"}, id="all_string"),
        pytest.param(
            {"cleanup_mode": "smart"},
            {"cleanup_mode": "smart"},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
