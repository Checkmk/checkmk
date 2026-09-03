#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.mysql.rulesets.bakery import migrate, migrate_credentials

_NEW_PASSWORD = ("cmk_postprocessed", "stored_password", ("pw_id", ""))
_NEW = {"deployment": ("cached", 300.0), "credentials": ("no_credentials", None), "host": "db"}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {},
            {
                "deployment": ("sync", None),
                "credentials": ("no_credentials", None),
                "sockets": [],
                "host": "",
                "custom_port": ("default", None),
            },
            id="old_empty_is_filled",
        ),
        pytest.param(
            {
                "interval": 300,
                "credentials": ("monitoring", ("store", "pw_id")),
                "sockets": [{"socket": "/var/run/mysqld/mysqld.sock"}],
                "host": "127.0.0.1",
                "custom_port": 3307,
            },
            {
                "deployment": ("cached", 300.0),
                "credentials": ("credentials", {"user": "monitoring", "password": _NEW_PASSWORD}),
                "sockets": [{"socket": "/var/run/mysqld/mysqld.sock"}],
                "host": "127.0.0.1",
                "custom_port": ("custom", 3307),
            },
            id="old_full",
        ),
        pytest.param(_NEW, _NEW, id="new"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_credentials_explicit_password() -> None:
    match migrate_credentials(("monitoring", ("password", "secret"))):
        case {
            "user": "monitoring",
            "password": ("cmk_postprocessed", "explicit_password", (str(), "secret")),
        }:
            pass
        case other:
            raise AssertionError(other)


def test_migrate_credentials_already_migrated() -> None:
    migrated = {"user": "root", "password": ("cmk_postprocessed", "stored_password", ("id", ""))}
    assert migrate_credentials(migrated) == migrated


@pytest.mark.parametrize("value", [pytest.param("root", id="str"), pytest.param([], id="list")])
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
