import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.mobileiron_sourcehost import check_mobileiron_sourcehost
from cmk.base.plugins.agent_based.mobileiron_section import parse_mobileiron_source_host

DEVICE_DATA = parse_mobileiron_source_host([['{"queryTime": 12, "total_count": 22}']])


@pytest.mark.parametrize(
    "section, expected_results",
    [
        (
            DEVICE_DATA,
            (
                Result(state=State.OK, summary="Query Time: 12"),
                Result(state=State.OK, summary="Total number of returned devices: 22"),
            ),
        ),
    ],
)
def test_check_mobileiron_sourcehost(section, expected_results) -> None:
    results = tuple(check_mobileiron_sourcehost(section))
    assert results == expected_results
