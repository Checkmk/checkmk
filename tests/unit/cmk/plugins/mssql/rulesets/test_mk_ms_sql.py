#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.exceptions import MKUserError
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.mssql.rulesets.mk_ms_sql import migrate, rule_spec_mk_ms_sql

_STORED = ("cmk_postprocessed", "stored_password", ("pw_id", ""))
_NEW_MINIMAL = {"deployment": ("sync", None), "main": {"auth": ("local", None)}, "other": []}

_OLD_SECTIONS = {
    "instance": "sync",
    "databases": "sync",
    "counters": "sync",
    "blocked_sessions": None,
    "transactionlogs": "sync",
    "clusters": "sync",
    "mirroring": "sync",
    "availability_groups": "sync",
    "connections": "sync",
    "tablespaces": "async",
    "datafiles": "async",
    "backup": "async",
    "jobs": None,
}


def _old_full(auth: object) -> dict[str, object]:
    """A rule as stored by the old rule set, with every parameter set"""
    return {
        "main": {
            "auth": auth,
            "conn": {"hostname": "h", "exclude_databases": ["model"]},
            "sections": _OLD_SECTIONS,
            "cache_age": 600,
            "discovery": (True, ("include", ["a"])),
            "instances": [
                {
                    "sid": "s",
                    "auth": "local",
                    "piggyback": {"hostname": "p", "sections": _OLD_SECTIONS},
                },
                {"sid": "t", "piggyback": {"sections": _OLD_SECTIONS}},
            ],
        },
        "other": [{"auth": "local", "conn": {"hostname": "o"}}],
    }


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param({"main": {"auth": "local"}}, _NEW_MINIMAL, id="old_minimal_is_filled"),
        pytest.param(
            {
                "main": {
                    "auth": ("remote", ("u", ("store", "pw_id"))),
                    "conn": {"hostname": "h", "exclude_databases": ["model"]},
                    "sections": {"instance": "sync", "transactionlogs": "async", "jobs": None},
                    "discovery": (True, ("include", ["a"])),
                    "instances": [
                        {
                            "sid": "s",
                            "auth": "local",
                            "piggyback": {"hostname": "p", "sections": {"backup": None}},
                        }
                    ],
                },
                "other": [{"auth": "local", "conn": {"hostname": "o"}}],
            },
            {
                "deployment": ("sync", None),
                "main": {
                    "auth": ("remote", {"user": "u", "password": _STORED}),
                    "conn": {"hostname": "h", "exclude_databases": ["model"]},
                    "sections": {
                        "instance": "sync",
                        "transactionlogs": "asynchronous",
                        "jobs": "disabled",
                    },
                    "discovery": {"detect": True, "instances": ("include", ["a"])},
                    "instances": [
                        {
                            "sid": "s",
                            "auth": ("local", None),
                            "piggyback": {"hostname": "p", "sections": {"backup": "disabled"}},
                        }
                    ],
                },
                "other": [{"auth": ("local", None), "conn": {"hostname": "o"}}],
            },
            id="old_full",
        ),
        pytest.param(
            {"main": {"auth": "local", "instances": [{"sid": "s", "piggyback": {}}]}},
            {
                "deployment": ("sync", None),
                "main": {"auth": ("local", None), "instances": [{"sid": "s"}]},
                "other": [],
            },
            id="old_piggyback_without_hostname",
        ),
        pytest.param(_NEW_MINIMAL, _NEW_MINIMAL, id="already_migrated"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_explicit_password() -> None:
    migrated = migrate({"main": {"auth": ("remote", ("u", ("password", "secret")))}})
    match migrated["main"]:
        case {
            "auth": ("remote", {"user": "u", "password": (_, "explicit_password", (_, "secret"))})
        }:
            pass
        case other:
            raise AssertionError(other)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("local", id="str"),
        pytest.param({}, id="empty_dict"),
        pytest.param({"other": []}, id="without_main"),
        pytest.param({"main": {"auth": "remote"}}, id="malformed_auth"),
        pytest.param(
            {"main": {"auth": "local", "discovery": (True, "none")}}, id="malformed_discovery"
        ),
        pytest.param(
            {"main": {"auth": "local", "sections": {"jobs": "cached"}}}, id="unknown_section_mode"
        ),
        pytest.param(
            {"main": {"auth": "local", "sections": {"jobs": []}}}, id="malformed_section_mode"
        ),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)


@pytest.mark.parametrize(
    "old",
    [
        pytest.param(None, id="do_not_deploy"),
        pytest.param({"main": {"auth": "local"}}, id="old_minimal"),
        pytest.param(_old_full(("remote", ("u", ("store", "pw_id")))), id="old_full"),
        pytest.param({"deployment": ("sync", None)}, id="new_without_main"),
    ],
)
def test_migrate_is_idempotent(old: object) -> None:
    migrated = migrate(old)
    assert migrate(migrated) == migrated


@pytest.mark.parametrize(
    "old",
    [
        pytest.param(None, id="do_not_deploy"),
        pytest.param({"main": {"auth": "local"}}, id="old_minimal"),
        # Validating a password needs a request context, so this uses local authentication.
        pytest.param(_old_full("local"), id="old_full"),
        pytest.param({"deployment": ("sync", None)}, id="new_without_main"),
    ],
)
def test_migrated_value_is_valid(old: object) -> None:
    valuespec = convert_to_legacy_rulespec(rule_spec_mk_ms_sql, Edition.PRO, lambda x: x).valuespec
    migrated = migrate(old)
    valuespec.validate_datatype(migrated, "")
    valuespec.validate_value(migrated, "")


def test_sections_must_be_complete() -> None:
    valuespec = convert_to_legacy_rulespec(rule_spec_mk_ms_sql, Edition.PRO, lambda x: x).valuespec
    with pytest.raises(MKUserError):
        valuespec.validate_datatype(
            {
                "deployment": ("sync", None),
                "main": {"auth": ("local", None), "sections": {"databases": "sync"}},
            },
            "",
        )
