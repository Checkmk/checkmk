#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.scaleio.rulesets.bakery import migrate

_NEW_PASSWORD = ("cmk_postprocessed", "explicit_password", ("uuid-1", "secret"))


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"user": "admin", "password": ("store", "pw_id"), "interval": 300},
            {
                "deployment": ("cached", 300.0),
                "user": "admin",
                "password": ("cmk_postprocessed", "stored_password", ("pw_id", "")),
            },
            id="interval_above_60_is_cached",
        ),
        pytest.param(
            {"user": "admin", "password": ("store", "pw_id"), "interval": 60},
            {
                "deployment": ("sync", None),
                "user": "admin",
                "password": ("cmk_postprocessed", "stored_password", ("pw_id", "")),
            },
            id="interval_of_60_is_sync",
        ),
        pytest.param(
            {"deployment": ("sync", None), "user": "admin", "password": _NEW_PASSWORD},
            {"deployment": ("sync", None), "user": "admin", "password": _NEW_PASSWORD},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_explicit_password() -> None:
    migrated = migrate({"user": "admin", "password": ("password", "secret"), "interval": 60})
    match migrated["password"]:
        case ("cmk_postprocessed", "explicit_password", (str(), "secret")):
            pass
        case other:
            raise AssertionError(other)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("admin", id="str"),
        pytest.param({}, id="empty"),
        pytest.param({"user": "admin"}, id="partial"),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
