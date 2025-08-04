#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.plugins.wato.check_parameters.fileinfo_groups import rule_spec_fileinfo_groups_checking
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {
                "minage_oldest": (36000, 36000),
                "maxage_oldest": (36000, 36000),
                "minage_newest": (36000, 36000),
                "maxage_newest": (0, 0),
                "minsize_smallest": (10, 10),
                "maxsize_smallest": (10, 10),
                "minsize_largest": (10, 10),
                "maxsize_largest": (10, 10),
                "minsize": (10, 10),
                "maxsize": (10, 10),
                "mincount": (10, 10),
                "maxcount": (10, 10),
                "conjunctions": [(2, [("size", 10)])],
                "negative_age_tolerance": 10,
            },
            id="rule with all parameters",
        ),
        pytest.param(
            {"minage_oldest": (36000, 36000), "maxage_oldest": (36000, 36000)},
            id="rule with minage_oldest and maxage_oldest only",
        ),
        pytest.param(
            {"minsize_smallest": (10, 10), "maxsize_smallest": (10, 10)},
            id="rule with minsize_smallest and maxsize_smallest only",
        ),
        pytest.param(
            {"minsize_largest": (10, 10), "maxsize_largest": (10, 10)},
            id="rule with minsize_largest and maxsize_largest only",
        ),
        pytest.param(
            {"minsize": (10, 10), "maxsize": (10, 10)},
            id="rule with minsize and maxsize only",
        ),
        pytest.param(
            {
                "conjunctions": [
                    (
                        2,
                        [
                            ("size", 10),
                            ("count", 20),
                            ("count_lower", 10),
                            ("size_lower", 10),
                            ("size_largest", 100),
                            ("size_largest_lower", 10),
                            ("age_newest", 36010),
                            ("age_oldest_lower", 36010),
                            ("age_newest_lower", 10),
                            ("age_oldest", 10),
                            ("size_smallest", 10),
                            ("size_smallest_lower", 10),
                        ],
                    )
                ]
            },
            id="rule with conjunctions only",
        ),
    ],
)
def test_rule_spec_fileinfo_groups_migration_validation(rule: dict[str, object]) -> None:
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_fileinfo_groups_checking, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule, "")
    validating_rule_spec.valuespec.validate_value(rule, "")
