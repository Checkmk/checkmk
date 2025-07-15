#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import ANY

import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.cisco.rulesets.cisco_prime import _migrate, rule_spec_cisco_prime


@pytest.mark.parametrize(
    ["rule_to_migrate", "expected_rule"],
    [
        pytest.param(
            {"host": "host_name"},
            {"host": ("host_name", None)},
            id="host_name",
        ),
        pytest.param(
            {"host": "ip_address"},
            {"host": ("ip_address", None)},
            id="ip_address",
        ),
        pytest.param(
            {"host": ("custom", {"host": "custom_host"})},
            {"host": ("custom", {"host": "custom_host"})},
            id="custom_host",
        ),
        pytest.param(
            {"basicauth": ("test_username", ("password", "test_password"))},
            {
                "basicauth": {
                    "username": "test_username",
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        (ANY, "test_password"),
                    ),
                }
            },
            id="explicit password",
        ),
        pytest.param(
            {"basicauth": ("test_username", ("store", "password_1"))},
            {
                "basicauth": {
                    "username": "test_username",
                    "password": ("cmk_postprocessed", "stored_password", ("password_1", "")),
                }
            },
            id="stored password",
        ),
        pytest.param(
            {"port": 1234, "no-tls": True, "no-cert-check": True, "timeout": 1},
            {"port": 1234, "no_tls": True, "no_cert_check": True, "timeout": 1},
            id="rest of rule",
        ),
    ],
)
def test_test_rule_spec_cisco_prime_migrate(
    rule_to_migrate: dict[str, object], expected_rule: dict[str, object]
) -> None:
    assert _migrate(rule_to_migrate) == expected_rule


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {
                "host": "host_name",
                "basicauth": ("test_username", ("password", "test_password")),
                "port": 1234,
                "no-tls": True,
                "no-cert-check": True,
                "timeout": 1,
            },
            id="2.2 rule",
        ),
        pytest.param(
            {
                "host": ("host_name", None),
                "basicauth": {
                    "username": "test_username",
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("uuidb010f99d-c4fd-48a8-894b-7845506f7825", "test_password"),
                    ),
                },
                "port": 1234,
                "no_tls": True,
                "no_cert_check": True,
                "timeout": 1,
            },
            id="2.3 rule",
        ),
    ],
)
def test_rule_spec_cisco_prime(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_cisco_prime, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
