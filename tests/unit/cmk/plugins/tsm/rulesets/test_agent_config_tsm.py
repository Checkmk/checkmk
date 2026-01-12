#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.tsm.rulesets.agent_config_tsm import _migrate


@pytest.mark.parametrize(
    "value,expected",
    [
        # v230p40
        (
            None,
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"user": "user", "password": "pass", "interval": 300},
            {
                "auth": {
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("some_uuid", "pass"),
                    ),
                    "user": "user",
                },
                "deployment": ("cached", 300.0),
            },
        ),
        (
            {"user": "user", "password": "pass"},
            {
                "auth": {
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("some_uuid", "pass"),
                    ),
                    "user": "user",
                },
                "deployment": ("sync", None),
            },
        ),
        # incorrectly migrated from v240p16
        (
            {"deployment": ("do_not_deploy", 0.0)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("sync", 300.0),
            },
            {
                "auth": {
                    "password": ("cmk_postprocessed", "explicit_password", ("some_uuid", "pass")),
                    "user": "user",
                },
                "deployment": ("cached", 300.0),
            },
        ),
        (
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("cached", None),
            },
            {
                "auth": {
                    "password": ("cmk_postprocessed", "explicit_password", ("some_uuid", "pass")),
                    "user": "user",
                },
                "deployment": ("sync", None),
            },
        ),
        # v240p16
        (
            {"deployment": ("sync", None), "cmk-match-type": "dict"},
            {"deployment": ("sync", None), "cmk-match-type": "dict"},
        ),
        (
            {"deployment": ("cached", 0.0), "cmk-match-type": "dict"},
            {"deployment": ("cached", 0.0), "cmk-match-type": "dict"},
        ),
        (
            {"deployment": ("do_not_deploy", None), "cmk-match-type": "dict"},
            {"deployment": ("do_not_deploy", None), "cmk-match-type": "dict"},
        ),
        (
            {"cmk-match-type": "dict"},
            {"cmk-match-type": "dict"},
        ),
        (
            {
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "explicit_password", ("some_uuid", "abc")),
                },
                "cmk-match-type": "dict",
            },
            {
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "explicit_password", ("some_uuid", "abc")),
                },
                "cmk-match-type": "dict",
            },
        ),
        (
            {
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "stored_password", ("password_1", "")),
                },
                "cmk-match-type": "dict",
            },
            {
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "stored_password", ("password_1", "")),
                },
                "cmk-match-type": "dict",
            },
        ),
    ],
)
def test_migrate(value: object, expected: dict[str, object]) -> None:
    migrated = _migrate(value)
    _assert_equal(migrated, expected)
    migrated_again = _migrate(value)
    _assert_equal(migrated, migrated_again)


def _replace_uuid(auth: object) -> None:
    if not isinstance(auth, dict):
        return
    match auth["password"]:
        case ("cmk_postprocessed", "explicit_password", (_uuid, password)):
            auth["password"] = ("cmk_postprocessed", "explicit_password", ("some_uuid", password))
        case _:
            pass


def _assert_equal(left: dict[str, object], right: dict[str, object]) -> None:
    assert left.get("deployment") == right.get("deployment")
    auth_left = left.get("auth")
    _replace_uuid(auth_left)
    auth_right = right.get("auth")
    _replace_uuid(auth_right)
    assert auth_left == auth_right
