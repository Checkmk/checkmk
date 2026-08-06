#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.mobileiron.agent_based.mobileiron_compliance import (
    check_mobileiron_compliance,
    Params,
)
from cmk.plugins.mobileiron.agent_based.mobileiron_section import parse_mobileiron
from cmk.plugins.mobileiron.lib import Section

DEVICE_DATA = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "entityName": "device1",
                    "complianceState": False,
                    "policyViolationCount": 4,
                    "id": "133",
                }
            )
        ]
    ]
)

COMPLIANT_DEVICE_DATA = parse_mobileiron(
    [
        [
            json.dumps(
                {
                    "entityName": "device1",
                    "complianceState": True,
                    "policyViolationCount": 4,
                    "id": "133",
                }
            )
        ]
    ]
)

NO_COUNT_DEVICE_DATA = parse_mobileiron(
    [[json.dumps({"entityName": "device1", "complianceState": True, "id": "133"})]]
)


@pytest.mark.parametrize(
    "params, section, expected_results",
    [
        (
            Params(policy_violation_levels=("fixed", (2, 3)), ignore_compliance=False),
            DEVICE_DATA,
            (
                Result(
                    state=State.CRIT,
                    summary="Policy violation count: 4 (warn/crit at 2/3)",
                ),
                Metric(
                    "mobileiron_policyviolationcount",
                    value=4,
                    levels=(2.0, 3.0),
                ),
                Result(state=State.CRIT, summary="Compliant: False"),
            ),
        ),
        (
            Params(policy_violation_levels=("fixed", (2, 3)), ignore_compliance=True),
            DEVICE_DATA,
            (
                Result(
                    state=State.CRIT,
                    summary="Policy violation count: 4 (warn/crit at 2/3)",
                ),
                Metric(
                    "mobileiron_policyviolationcount",
                    value=4,
                    levels=(2.0, 3.0),
                ),
                Result(state=State.OK, summary="Compliant: False (ignored)"),
            ),
        ),
        (
            Params(policy_violation_levels=("fixed", (3, 5)), ignore_compliance=False),
            DEVICE_DATA,
            (
                Result(
                    state=State.WARN,
                    summary="Policy violation count: 4 (warn/crit at 3/5)",
                ),
                Metric(
                    name="mobileiron_policyviolationcount",
                    value=4,
                    levels=(3.0, 5.0),
                ),
                Result(state=State.CRIT, summary="Compliant: False"),
            ),
        ),
        (
            Params(policy_violation_levels=("fixed", (3, 5)), ignore_compliance=False),
            COMPLIANT_DEVICE_DATA,
            (
                Result(
                    state=State.WARN,
                    summary="Policy violation count: 4 (warn/crit at 3/5)",
                ),
                Metric(
                    name="mobileiron_policyviolationcount",
                    value=4,
                    levels=(3.0, 5.0),
                ),
                Result(state=State.OK, summary="Compliant: True"),
            ),
        ),
        (
            Params(policy_violation_levels=("fixed", (3, 5)), ignore_compliance=False),
            NO_COUNT_DEVICE_DATA,
            (
                Result(
                    state=State.OK,
                    summary="Policy violation count: 0",
                ),
                Metric(
                    name="mobileiron_policyviolationcount",
                    value=0,
                    levels=(3.0, 5.0),
                ),
                Result(state=State.OK, summary="Compliant: True"),
            ),
        ),
    ],
)
def test_check_mobileiron_compliance(
    params: Params, section: Section, expected_results: CheckResult
) -> None:
    results = tuple(check_mobileiron_compliance(params, section))
    assert results == expected_results
