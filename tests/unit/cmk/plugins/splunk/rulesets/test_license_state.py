#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.splunk.rulesets.license_state import rule_spec_check_parameters


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {"state": 2},
            id="no expiration time",
        ),
        pytest.param(
            {"state": 3, "expiration_time": (1209600, 604800)},
            id="2.3 rule",
        ),
        pytest.param(
            {"expiration_time": (1209600, 0)},
            id="2.3 rule, zero warn level",
        ),
        pytest.param(
            {"state": 2, "expiration_time": ("fixed", (1209600, 604800))},
            id="2.4 rule",
        ),
    ],
)
def test_rule_spec_license_state_migration_validation(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_check_parameters, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
