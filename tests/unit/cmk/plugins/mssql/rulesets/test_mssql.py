#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.mssql.rulesets.mssql import migrate, migrate_auth

_NEW = {
    "deployment": ("sync", None),
    "auth_default": ("system", None),
    "auth_instances": [
        {
            "instance": "INST",
            "auth": (
                "db",
                {"user": "u", "password": ("cmk_postprocessed", "stored_password", ("pw", ""))},
            ),
        }
    ],
    "inst_excludes": ["x"],
}
_FILLED_MINIMAL = {
    "deployment": ("sync", None),
    "auth_default": ("system", None),
    "auth_instances": [],
    "inst_excludes": [],
    "timeout_connection": 15,
    "timeout_command": 30,
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param({"auth_default": "system"}, _FILLED_MINIMAL, id="old_minimal_is_filled"),
        pytest.param({}, _FILLED_MINIMAL, id="old_empty_is_filled"),
        pytest.param(_NEW, _NEW, id="new"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_instances_with_plain_text_password() -> None:
    migrated = migrate(
        {
            "auth_default": "system",
            "auth_instances": [("INST", ("db", ("u", "secret")))],
            "inst_excludes": ["x"],
            "timeout_command": 10,
        }
    )
    assert migrated["timeout_connection"] == 15
    assert migrated["timeout_command"] == 10
    match migrated["auth_instances"]:
        case [
            {
                "instance": "INST",
                "auth": (
                    "db",
                    {
                        "user": "u",
                        "password": ("cmk_postprocessed", "explicit_password", (str(), "secret")),
                    },
                ),
            }
        ]:
            pass
        case other:
            raise AssertionError(other)


def test_migrate_auth_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        migrate_auth("unexpected")


@pytest.mark.parametrize("value", [pytest.param("system", id="str"), pytest.param([], id="list")])
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
