#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import lru_cache

import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs import legacy_converter
from cmk.gui.valuespec import ValueSpec
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.plugins.emailchecks.rulesets.active_check_mail import rule_spec_mail
from cmk.utils.rulesets.definition import RuleGroup


@lru_cache
def _check_mail_vs() -> ValueSpec:
    all_rulesets = AllRulesets.load_all_rulesets().get_rulesets()
    try:
        return all_rulesets[RuleGroup.ActiveChecks("mail")].valuespec()
    except KeyError:
        raise RuntimeError(sorted(all_rulesets))


def migrate(old: object) -> object:
    return _check_mail_vs().transform_value(old)


def test_minimal_migration_validation() -> None:
    rule = {
        "service_description": "Email",
        "connect_timeout": 10,
        "fetch": (
            "IMAP",
            {
                "server": "",
                "connection": {"disable_tls": False, "disable_cert_validation": False},
                "auth": ("basic", ("foo", ("password", "123"))),
            },
        ),
    }

    converted = legacy_converter.convert_to_legacy_rulespec(
        rule_spec_mail, Edition.CEE, lambda x: x
    ).valuespec

    converted.validate_datatype(rule, "")
    rule_transformed = converted.transform_value(rule)
    converted.validate_value(rule_transformed, "")


def test_migration_minimal_config(request_context: None) -> None:
    new = migrate(
        {
            "service_description": "unchanged",
            "fetch": (
                "IMAP",
                {
                    "connection": {"disable_tls": False, "port": 143},
                    "auth": ("basic", ("foo", ("password", "bar"))),
                },
            ),
        }
    )
    match new:
        case {
            "service_description": "unchanged",
            "fetch": (
                "IMAP",
                {
                    "auth": (
                        "basic",
                        {
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                (
                                    str(),  # some uuid.
                                    "bar",
                                ),
                            ),
                            "username": "foo",
                        },
                    ),
                    "connection": {
                        "disable_tls": False,
                        "port": 143,
                    },
                },
            ),
        }:
            pass
        case _:
            raise AssertionError(new)


def test_migration_connect_timeout_is_float(request_context: None) -> None:
    new = migrate({"connect_timeout": 15})
    assert isinstance(new, dict) and isinstance(
        new["connect_timeout"],
        float,
    )


@pytest.mark.parametrize(
    "old, new",
    [
        ("", ("ec", ("local", ""))),
        ("string", ("ec", ("socket", "string"))),
        ("spool:", ("ec", ("spool_local", ""))),
        ("spool:string", ("ec", ("spool", "string"))),
        (
            ("udp", "localhost", 123),
            ("syslog", {"protocol": "udp", "address": "localhost", "port": 123}),
        ),
        (
            ("tcp", "localhort", 456),
            ("syslog", {"protocol": "tcp", "address": "localhort", "port": 456}),
        ),
    ],
)
def test_migration_forward_method(old: str, new: object, request_context: None) -> None:
    assert migrate({"forward": {"method": old}}) == {"forward": {"method": new}}


def test_migration_forward(request_context: None) -> None:
    assert migrate(
        {
            "forward": {
                "facility": 2,
                "application": None,
                "host": "me.too@checkmk.com",
                "body_limit": 1000,
                "cleanup": True,
            },
        }
    ) == {
        "forward": {
            "facility": ("mail", 2),
            "application": ("subject", None),
            "host": "me.too@checkmk.com",
            "body_limit": 1000,
            "cleanup": ("delete", "delete"),
        },
    }
