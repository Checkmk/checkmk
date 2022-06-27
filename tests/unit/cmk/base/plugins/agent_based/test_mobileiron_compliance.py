#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.mobileiron_compliance import check_mobileiron_compliance
from cmk.base.plugins.agent_based.mobileiron_section import parse_mobileiron

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
            {},
            DEVICE_DATA,
            (
                Result(
                    state=State.OK,
                    summary="Policy violation count: 4",
                ),
                Metric(
                    "mobileiron_policyviolationcount",
                    value=4,
                ),
                Result(state=State.CRIT, summary="Compliance state: False"),
            ),
        ),
        (
            {"policy_violation_levels": (3, 5)},
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
                Result(state=State.CRIT, summary="Compliance state: False"),
            ),
        ),
        (
            {"policy_violation_levels": (3, 5)},
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
                Result(state=State.OK, summary="Compliance state: True"),
            ),
        ),
        (
            {"policy_violation_levels": (3, 5)},
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
                Result(state=State.OK, summary="Compliance state: True"),
            ),
        ),
    ],
)
def test_check_mobileiron_compliance(params, section, expected_results) -> None:
    results = tuple(check_mobileiron_compliance(params, section))
    assert results == expected_results
