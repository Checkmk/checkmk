import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.mobileiron_misc import check_mobileiron_misc
from cmk.base.plugins.agent_based.utils.mobileiron import parse_mobileiron

DEVICE_DATA = parse_mobileiron(
    [
        [
            '{"entityName": "device1",'
            ' "availableCapacity": 55.1,'
            ' "uptime": 105430703,'
            ' "ipAddress": "1.1.1.1",'
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
                    summary="Available capacity: 55.10%",
                ),
                Metric(
                    "capacity_perc",
                    value=55.1,
                ),
                Result(state=State.OK, summary="IP address: 1.1.1.1"),
            ),
        ),
        (
            {"available_capacity": (50.0, 70.0)},
            DEVICE_DATA,
            (
                Result(
                    state=State.WARN,
                    summary="Available capacity: 55.10% (warn/crit at 50.00%/70.00%)",
                ),
                Metric(
                    name="capacity_perc",
                    value=55.1,
                    levels=(50.0, 70.0),
                ),
                Result(state=State.OK, summary="IP address: 1.1.1.1"),
            ),
        ),
    ],
)
def test_check_mobileiron_misc(params, section, expected_results) -> None:
    results = tuple(check_mobileiron_misc(params, section))
    assert results == expected_results
