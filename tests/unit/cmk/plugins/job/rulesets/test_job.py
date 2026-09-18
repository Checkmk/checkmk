#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.job.agent_based.job import check_plugin_job
from cmk.plugins.job.rulesets.job import rule_spec_job


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param({}, {}, id="empty rule"),
        pytest.param(
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            {"age": ("no_levels", None), "exit_code_to_state_map": [{"exit_code": 0, "state": 0}]},
            # These were the defaults of the check plug-in, and it applied neither of them.
            id="pre v1 API defaults",
        ),
        pytest.param(
            {"age": (3600, 7200), "exit_code_to_state_map": [(1, 1), (2, 3)]},
            {
                "age": ("fixed", (3600.0, 7200.0)),
                "exit_code_to_state_map": [
                    {"exit_code": 1, "state": 1},
                    {"exit_code": 2, "state": 3},
                ],
            },
            id="pre v1 API levels and mapping",
        ),
        pytest.param(
            {
                "age": ("fixed", (3600.0, 7200.0)),
                "exit_code_to_state_map": [{"exit_code": 1, "state": 1}],
            },
            {
                "age": ("fixed", (3600.0, 7200.0)),
                "exit_code_to_state_map": [{"exit_code": 1, "state": 1}],
            },
            id="already migrated",
        ),
    ],
)
def test_rule_spec_job(rule: dict[str, object], expected: dict[str, object]) -> None:
    valuespec = convert_to_legacy_rulespec(rule_spec_job, Edition.COMMUNITY, lambda x: x).valuespec

    migrated = valuespec.transform_value(rule)

    assert migrated == expected
    valuespec.validate_datatype(migrated, "")
    valuespec.validate_value(migrated, "")


def test_check_default_parameters_are_valid() -> None:
    valuespec = convert_to_legacy_rulespec(rule_spec_job, Edition.COMMUNITY, lambda x: x).valuespec

    assert (defaults := check_plugin_job.check_default_parameters) is not None

    valuespec.validate_datatype(dict(defaults), "")
    valuespec.validate_value(dict(defaults), "")
