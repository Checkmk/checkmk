import pytest

from cmk.base.plugins.agent_based import synology_fans
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State

SECTION_TABLE = [
    ["1", "0"],
]


def test_parsing():
    section = synology_fans.parse(SECTION_TABLE)
    assert section == {"System": 1, "CPU": 0}


def test_discovery():
    section = synology_fans.parse(SECTION_TABLE)
    assert section is not None
    services = list(synology_fans.discovery(section))
    assert set(s.item for s in services) == {"System", "CPU"}


@pytest.mark.parametrize(
    "item, expected",
    [("System", State.CRIT), ("CPU", State.OK)],
)
def test_result_state(item, expected):
    section = synology_fans.parse(SECTION_TABLE)
    assert section is not None
    result = list(synology_fans.check(item=item, section=section))[0]
    assert isinstance(result, Result)
    assert result.state == expected
