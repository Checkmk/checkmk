#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.redis.rulesets.bakery import migrate, migrate_instance, rule_spec_mk_redis

_STORED = ("cmk_postprocessed", "stored_password", ("pw_id", ""))
_TCP = ("tcp", {"host": "127.0.0.1", "port": 6379})
_NEW_INSTANCE = {"instance": "inst1", "connection": _TCP, "password": ("password", _STORED)}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            "autodetect",
            {"deployment": ("sync", None), "instances": ("autodetect", None)},
            id="autodetect",
        ),
        pytest.param(
            ("static", [{"instance": "inst1", "connection": _TCP, "password": ("store", "pw_id")}]),
            {"deployment": ("sync", None), "instances": ("static", [_NEW_INSTANCE])},
            id="static",
        ),
        pytest.param(
            {"deployment": ("sync", None), "instances": ("static", [_NEW_INSTANCE])},
            {"deployment": ("sync", None), "instances": ("static", [_NEW_INSTANCE])},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"instance": "inst1", "connection": _TCP, "password": None},
            {"instance": "inst1", "connection": _TCP, "password": ("no_password", None)},
            id="no_password",
        ),
        pytest.param(
            {"instance": "inst1", "connection": _TCP, "password": ("store", "pw_id")},
            _NEW_INSTANCE,
            id="stored_password",
        ),
        pytest.param(
            {
                "instance": "inst1",
                "connection": ("unix-socket", {"socket": "/path/to/socket"}),
                "password": ("no_password", None),
            },
            {
                "instance": "inst1",
                "connection": ("unix_socket", {"socket": "/path/to/socket"}),
                "password": ("no_password", None),
            },
            id="unix_socket",
        ),
        pytest.param(_NEW_INSTANCE, _NEW_INSTANCE, id="already_migrated"),
    ],
)
def test_migrate_instance(old: object, expected: dict[str, object]) -> None:
    assert migrate_instance(old) == expected


def test_migrate_instance_explicit_password() -> None:
    match migrate_instance({"instance": "i", "connection": _TCP, "password": ("password", "s")})[
        "password"
    ]:
        case ("password", ("cmk_postprocessed", "explicit_password", (str(), "s"))):
            pass
        case other:
            raise AssertionError(other)


@pytest.mark.parametrize("value", ["static", {}, ("static", "inst1")])
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)


def test_migrate_instance_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        migrate_instance(("inst1", _TCP))


def test_form_spec_can_be_built() -> None:
    rule_spec_mk_redis.parameter_form()
