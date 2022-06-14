import pytest

from tests.unit.cmk.base.plugins.agent_based.test_gcp_gcs import SECTION_TABLE

from cmk.base.plugins.agent_based import synology_disks
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

SECTION_TABLE = [
    ["Disk 1", "WD40EFAX-68JH4N0", "1", "33"],
    ["Disk 2", "WD40EFAX-68JH4N0", "2", "33"],
    ["Disk 3", "WD40EFAX-68JH4N0", "3", "33"],
    ["Disk 4", "WD40EFAX-68JH4N0", "4", "33"],
    ["Disk 5", "WD40EFAX-68JH4N0", "5", "33"],
]


def test_parsing() -> None:
    section = synology_disks.parse_synology(SECTION_TABLE)
    assert len(section) == len(SECTION_TABLE)


def test_discovery() -> None:
    section = synology_disks.parse_synology(SECTION_TABLE)
    services = list(synology_disks.discover_synology_disks(section))
    assert set(s.item for s in services) == set(el[0] for el in SECTION_TABLE)


def make_section(
    state: int = 1, temperature: float = 42.1, disk: str = "none", model="hello"
) -> synology_disks.Section:
    return {disk: synology_disks.Disk(state=state, temperature=temperature, disk=disk, model=model)}


@pytest.mark.parametrize(
    "state, expected",
    [(1, State.OK), (2, State.OK), (3, State.WARN), (4, State.CRIT), (5, State.CRIT)],
)
def test_result_state(state, expected) -> None:
    section = make_section(state=state)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))[-1]
    assert isinstance(result, Result)
    assert result.state == expected


def test_temperature_metric() -> None:
    temperature = 42.0
    section = make_section(temperature=temperature)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))[0]
    assert isinstance(result, Metric)
    assert result.value == temperature
    assert result.name == "temp"


@pytest.mark.parametrize("model, expected", [("mSSD", True), ("mNVME", True), ("HDD", None)])
def test_discovery_detect_cached(model, expected) -> None:
    section = make_section(model=model, state=3)
    service = list(synology_disks.discover_synology_disks(section))[0]
    assert service.parameters.get("used_as_cache") == expected


@pytest.mark.parametrize("used_as_cache, expected", [(True, State.OK), (False, State.WARN)])
def test_check_cached_is_ok(used_as_cache, expected) -> None:
    section = make_section(state=3)
    item = list(section.keys())[0]
    params = {"used_as_cache": used_as_cache}
    result = list(synology_disks.check_synology_disks(section=section, item=item, params=params))[
        -1
    ]
    assert isinstance(result, Result)
    assert result.state == expected
