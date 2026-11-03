#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.sap_hana.rulesets.bakery import migrate

_STORED = ("cmk_postprocessed", "stored_password", ("pw_id", ""))


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"credentials": "storekey", "runas": "agent"},
            {
                "deployment": ("sync", ("userstorekey", "storekey")),
                "credentials_sap_connect": ("none", None),
                "runas": "agent",
            },
            id="old_userstorekey_with_runas",
        ),
        pytest.param(
            {
                "credentials": ("peter", ("store", "pw_id")),
                "credentials_sap_connect": ("connect", ("store", "pw_id")),
            },
            {
                "deployment": ("sync", ("user_password", {"user": "peter", "password": _STORED})),
                "credentials_sap_connect": (
                    "credentials",
                    {"user": "connect", "password": _STORED},
                ),
                "runas": "instance",
            },
            id="old_user_password_with_connect_is_filled",
        ),
        pytest.param(
            {
                "credentials": [
                    ("sid1", "inst1", "db1", ("usr1", ("store", "pw_id"))),
                    ("sid2", "inst2", "db2", "storekey2"),
                ]
            },
            {
                "deployment": (
                    "sync",
                    (
                        "databases",
                        [
                            {
                                "sid": "sid1",
                                "instance": "inst1",
                                "database": "db1",
                                "credentials": (
                                    "user_password",
                                    {"user": "usr1", "password": _STORED},
                                ),
                            },
                            {
                                "sid": "sid2",
                                "instance": "inst2",
                                "database": "db2",
                                "credentials": ("userstorekey", "storekey2"),
                            },
                        ],
                    ),
                ),
                "credentials_sap_connect": ("none", None),
                "runas": "instance",
            },
            id="old_databases",
        ),
        pytest.param(
            {"deployment": ("sync", ("userstorekey", "k"))},
            {"deployment": ("sync", ("userstorekey", "k"))},
            id="new",
        ),
        pytest.param(
            {
                "credentials": ("userstorekey", ("store", "pw_id")),
                "credentials_sap_connect": ("credentials", ("store", "pw_id")),
            },
            {
                "deployment": (
                    "sync",
                    ("user_password", {"user": "userstorekey", "password": _STORED}),
                ),
                "credentials_sap_connect": (
                    "credentials",
                    {"user": "credentials", "password": _STORED},
                ),
                "runas": "instance",
            },
            id="old_user_named_like_a_new_variant",
        ),
        pytest.param(
            {"credentials": ("databases", ("store", "pw_id"))},
            {
                "deployment": (
                    "sync",
                    ("user_password", {"user": "databases", "password": _STORED}),
                ),
                "credentials_sap_connect": ("none", None),
                "runas": "instance",
            },
            id="old_user_named_databases",
        ),
        pytest.param(
            {"credentials": [("sid1", "inst1", "db1", ("user_password", ("store", "pw_id")))]},
            {
                "deployment": (
                    "sync",
                    (
                        "databases",
                        [
                            {
                                "sid": "sid1",
                                "instance": "inst1",
                                "database": "db1",
                                "credentials": (
                                    "user_password",
                                    {"user": "user_password", "password": _STORED},
                                ),
                            }
                        ],
                    ),
                ),
                "credentials_sap_connect": ("none", None),
                "runas": "instance",
            },
            id="old_database_user_named_user_password",
        ),
        pytest.param(
            {},
            {"deployment": ("do_not_deploy", None)},
            id="old_without_credentials",
        ),
        pytest.param(
            {"runas": "agent"},
            {"deployment": ("do_not_deploy", None)},
            id="old_without_credentials_with_runas",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_explicit_password() -> None:
    migrated = migrate({"credentials": ("peter", ("password", "secret"))})
    match migrated["deployment"]:
        case (
            "sync",
            (
                "user_password",
                {
                    "user": "peter",
                    "password": ("cmk_postprocessed", "explicit_password", (str(), "secret")),
                },
            ),
        ):
            pass
        case other:
            raise AssertionError(other)


def test_migrate_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        migrate("storekey")
