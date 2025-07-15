#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.cisco_meraki.rulesets.agent_cisco_meraki import rule_spec_cisco_meraki


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {
                "api_key": ("password", "test-password"),
                "orgs": ["test-1", "test-2"],
                "proxy": ("no_proxy", None),
                "sections": ["licenses-overview", "device-statuses", "sensor-readings"],
            },
            id="2.2 rule no proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "test-password"),
                "orgs": ["test-1", "test-2"],
                "proxy": ("url", "https://example.com"),
                "sections": ["licenses-overview", "device-statuses", "sensor-readings"],
            },
            id="2.2 rule proxy url",
        ),
    ],
)
def test_rule_spec_cisco_prime_migration_validation(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_cisco_meraki, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
