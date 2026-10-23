#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.windows_sections import migrate_sections


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param([], {"sections": []}, id="empty_list"),
        pytest.param(["check_mk", "df"], {"sections": ["check_mk", "df"]}, id="list"),
        pytest.param({"sections": ["df"]}, {"sections": ["df"]}, id="already_migrated"),
    ],
)
def test_migrate_sections(old: object, expected: dict[str, object]) -> None:
    assert migrate_sections(old) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("df", id="str"),
        pytest.param(None, id="none"),
        pytest.param({}, id="empty_dict"),
    ],
)
def test_migrate_sections_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate_sections(value)
