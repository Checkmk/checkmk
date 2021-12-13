import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.mobileiron_compliance import check_mobileiron_compliance
from cmk.base.plugins.agent_based.utils.mobileiron import parse_mobileiron

DEVICE_DATA = parse_mobileiron(
    [
        [
            '{"entityName": "device1",'
            ' "complianceState": false,'
            ' "policyViolationCount": 4,'
            ' "id": "133"}'
        ]
    ]
)

COMPLIANT_DEVICE_DATA = parse_mobileiron(
    [
        [
            '{"entityName": "device1",'
            ' "complianceState": true,'
            ' "policyViolationCount": 4,'
            ' "id": "133"}'
        ]
    ]
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
    ],
)
def test_check_mobileiron_compliance(params, section, expected_results) -> None:
    results = tuple(check_mobileiron_compliance(params, section))
    assert results == expected_results
