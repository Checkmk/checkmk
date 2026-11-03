#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.checkmk.rulesets.mk_inventory import migrate

_REG = [r"Software\Microsoft\Windows\CurrentVersion\Uninstall"]


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {},
            {
                "deployment": ("sync", None),
                "interval": 14400.0,
                "exe_paths": [],
                "reg_paths": ("custom", []),
            },
            id="old_empty",
        ),
        pytest.param(
            {"interval": 14400, "reg_paths": _REG},
            {
                "deployment": ("sync", None),
                "interval": 14400,
                "exe_paths": [],
                "reg_paths": ("custom", _REG),
            },
            id="old_partial",
        ),
        pytest.param(
            {"interval": 60, "exe_paths": ["C:\\tools"], "reg_paths": _REG},
            {
                "deployment": ("sync", None),
                "interval": 60,
                "exe_paths": ["C:\\tools"],
                "reg_paths": ("custom", _REG),
            },
            id="old_full",
        ),
        pytest.param(
            {"interval": 60, "exe_paths": [], "reg_paths": []},
            {
                "deployment": ("sync", None),
                "interval": 60,
                "exe_paths": [],
                "reg_paths": ("custom", []),
            },
            id="old_explicit_empty_lists",
        ),
        pytest.param(
            {"deployment": ("sync", None), "interval": 60.0},
            {"deployment": ("sync", None), "interval": 60.0},
            id="new",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value", [pytest.param("unexpected", id="str"), pytest.param([], id="list")]
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
