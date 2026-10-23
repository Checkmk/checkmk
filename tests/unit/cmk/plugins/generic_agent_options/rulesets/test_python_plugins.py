#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.generic_agent_options.rulesets.python_plugins import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"version": "python3"},
            {"python_version": "python3", "command": ""},
            id="old_no_command",
        ),
        pytest.param(
            {"version": "auto", "command": "/opt/python"},
            {"python_version": "auto", "command": "/opt/python"},
            id="old_full",
        ),
        pytest.param({"python_version": "python2"}, {"python_version": "python2"}, id="new"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value",
    [pytest.param({}, id="empty"), pytest.param(None, id="none"), pytest.param("auto", id="str")],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
