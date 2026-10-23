#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_controller import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"check_controller_access": True, "force_legacy": False},
            {"check_access": True, "allow_legacy": False, "agent_channel": ("mailslot", None)},
            id="old_without_channel",
        ),
        pytest.param(
            {"check_controller_access": False, "force_legacy": True, "agent_channel": ("tcp", 1)},
            {"check_access": False, "allow_legacy": True, "agent_channel": ("tcp", 1)},
            id="old_with_channel",
        ),
        pytest.param(
            {"check_access": True, "allow_legacy": True},
            {"check_access": True, "allow_legacy": True},
            id="new",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value",
    [pytest.param({}, id="empty"), pytest.param(None, id="none"), pytest.param("tcp", id="str")],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
