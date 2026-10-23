#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.msoffice.rulesets.bakery import migrate

_NEW_PASSWORD = ("cmk_postprocessed", "explicit_password", ("uuid-1", "secret789"))
_MIGRATED = {
    "deployment": ("sync", None),
    "client_id": "abc123",
    "tenant_id": "xyz456",
    "client_secret": _NEW_PASSWORD,
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(_MIGRATED, _MIGRATED, id="already_migrated"),
        pytest.param(
            {"client_id": "abc123", "tenant_id": "xyz456", "client_secret": ("store", "pw_id")},
            {
                "deployment": ("sync", None),
                "client_id": "abc123",
                "tenant_id": "xyz456",
                "client_secret": ("cmk_postprocessed", "stored_password", ("pw_id", "")),
            },
            id="stored_password",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_explicit_password() -> None:
    migrated = migrate(
        {"client_id": "abc123", "tenant_id": "xyz456", "client_secret": ("password", "secret789")}
    )
    match migrated["client_secret"]:
        case ("cmk_postprocessed", "explicit_password", (str(), "secret789")):
            pass
        case other:
            raise AssertionError(other)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("abc123", id="str"),
        pytest.param({}, id="empty"),
        pytest.param({"client_id": "abc123"}, id="partial"),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
