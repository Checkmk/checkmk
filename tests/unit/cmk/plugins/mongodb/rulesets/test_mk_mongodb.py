#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.mongodb.rulesets.bakery import migrate, migrate_auth


@pytest.mark.parametrize(
    ["value", "expected"],
    [
        (None, {"deployment": ("do_not_deploy", None)}),
        (True, {"deployment": ("sync", None)}),
        (
            {
                "auth_mechanism": "DEFAULT",
                "auth_source": "admin",
                "username": "user",
                "password": ("password", "secret"),
            },
            {
                "deployment": ("sync", None),
                "auth": {
                    "auth_mechanism": "DEFAULT",
                    "auth_source": "admin",
                    "username": "user",
                    "password": ("password", "secret"),
                },
            },
        ),
        (
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"deployment": ("sync", None), "auth": {"auth_mechanism": "DEFAULT"}},
            {"deployment": ("sync", None), "auth": {"auth_mechanism": "DEFAULT"}},
        ),
    ],
    ids=[
        "none_to_do_not_deploy",
        "true_to_sync",
        "old_auth_dict_wrapped",
        "already_migrated_sync",
        "already_migrated_do_not_deploy",
        "already_migrated_with_auth",
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected


def test_migrate_auth_migrates_old_password() -> None:
    result = migrate_auth(
        {
            "auth_mechanism": "DEFAULT",
            "auth_source": "admin",
            "username": "user",
            "password": ("password", "secret"),
        }
    )
    assert isinstance(result, dict)
    assert result["auth_mechanism"] == "DEFAULT"
    pw = result["password"]
    assert isinstance(pw, tuple)
    assert pw[0] == "cmk_postprocessed"
    assert pw[1] == "explicit_password"
    assert pw[2][1] == "secret"


@pytest.mark.parametrize(
    ["value", "expected"],
    [
        (
            {
                "auth_mechanism": "DEFAULT",
                "auth_source": "admin",
                "username": "user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid-1", "secret"),
                ),
            },
            {
                "auth_mechanism": "DEFAULT",
                "auth_source": "admin",
                "username": "user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid-1", "secret"),
                ),
            },
        ),
        (
            {"auth_mechanism": "DEFAULT", "auth_source": "admin", "username": "user"},
            {"auth_mechanism": "DEFAULT", "auth_source": "admin", "username": "user"},
        ),
    ],
    ids=[
        "passes_through_already_migrated_password",
        "no_password_key_passes_through",
    ],
)
def test_migrate_auth(value: object, expected: object) -> None:
    assert migrate_auth(value) == expected
