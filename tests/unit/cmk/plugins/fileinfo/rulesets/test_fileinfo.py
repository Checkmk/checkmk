#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.plugins.wato.check_parameters.fileinfo import rule_spec_fileinfo
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {
                "minage": (864000, 864000),
                "maxage": (864000, 864000),
                "minsize": (10, 10),
                "maxsize": (10, 10),
                "state_missing": 1,
                "negative_age_tolerance": 600,
            },
            id="rule with all parameters",
        ),
        pytest.param(
            {"minage": (864000, 864000), "maxage": (864000, 864000)},
            id="rule with minage and maxage only",
        ),
        pytest.param(
            {"minsize": (10, 10), "maxsize": (10, 10)},
            id="rule with minsize and maxsize only",
        ),
        pytest.param(
            {"state_missing": 1},
            id="rule with state_missing only",
        ),
        pytest.param(
            {"negative_age_tolerance": 600},
            id="rule with negative_age_tolerance only",
        ),
    ],
)
def test_rule_spec_fileinfo_migration_validation(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(rule_spec_fileinfo, Edition.CRE, lambda x: x)
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
