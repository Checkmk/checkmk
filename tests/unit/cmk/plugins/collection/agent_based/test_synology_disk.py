#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.unit.cmk.plugins.collection.agent_based.snmp import get_parsed_snmp_section

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import synology_disks

# SUP-13080
DATA_0 = """
.1.3.6.1.2.1.1.1.0 Linux PPPPPP 1.1.111+ #00000 SMP Tue Nov 11 11:11:11 CST 1111 x86_64
.1.3.6.1.4.1.6574.2.1.1.2.0 Disk 1
.1.3.6.1.4.1.6574.2.1.1.2.1 Disk 2
.1.3.6.1.4.1.6574.2.1.1.2.2 Disk 3
.1.3.6.1.4.1.6574.2.1.1.2.3 Disk 4
.1.3.6.1.4.1.6574.2.1.1.3.0 HAT5300-8T
.1.3.6.1.4.1.6574.2.1.1.3.1 HAT5300-8T
.1.3.6.1.4.1.6574.2.1.1.3.2 HAT5300-8T
.1.3.6.1.4.1.6574.2.1.1.3.3 HAT5300-8T
.1.3.6.1.4.1.6574.2.1.1.5.0 1
.1.3.6.1.4.1.6574.2.1.1.5.1 1
.1.3.6.1.4.1.6574.2.1.1.5.2 1
.1.3.6.1.4.1.6574.2.1.1.5.3 1
.1.3.6.1.4.1.6574.2.1.1.6.0 27
.1.3.6.1.4.1.6574.2.1.1.6.1 26
.1.3.6.1.4.1.6574.2.1.1.6.2 26
.1.3.6.1.4.1.6574.2.1.1.6.3 25
.1.3.6.1.4.1.6574.2.1.1.7.0 data
.1.3.6.1.4.1.6574.2.1.1.7.1 data
.1.3.6.1.4.1.6574.2.1.1.7.2 data
.1.3.6.1.4.1.6574.2.1.1.7.3 data
.1.3.6.1.4.1.6574.2.1.1.13.0 1
.1.3.6.1.4.1.6574.2.1.1.13.1 1
.1.3.6.1.4.1.6574.2.1.1.13.2 3
.1.3.6.1.4.1.6574.2.1.1.13.3 1
"""

DATA_1 = """
.1.3.6.1.4.1.6574.2.1.1.2.0 Disk 1
.1.3.6.1.4.1.6574.2.1.1.3.0 HAT5300-8T
.1.3.6.1.4.1.6574.2.1.1.5.0 1
.1.3.6.1.4.1.6574.2.1.1.6.0 27
"""

# SUP-13490
DATA_2 = """
.1.3.6.1.4.1.6574.2.1.1.2.3 Disk 4
.1.3.6.1.4.1.6574.2.1.1.3.3 WD40000000-6666666
.1.3.6.1.4.1.6574.2.1.1.5.3 3
.1.3.6.1.4.1.6574.2.1.1.6.3 35
.1.3.6.1.4.1.6574.2.1.1.7.3 hotspare
"""

SECTION_TABLE = [
    ["Disk 1", "WD40EFAX-68JH4N0", "1", "33", "data", "1"],
    ["Disk 2", "WD40EFAX-68JH4N0", "2", "33", "data", "1"],
    ["Disk 3", "WD40EFAX-68JH4N0", "3", "33", "data", "1"],
    ["Disk 4", "WD40EFAX-68JH4N0", "4", "33", "data", "1"],
    ["Disk 5", "WD40EFAX-68JH4N0", "5", "33", "data", "1"],
]


def test_parsing() -> None:
    section = synology_disks.parse_synology(SECTION_TABLE)
    assert len(section) == len(SECTION_TABLE)


def test_discovery() -> None:
    section = synology_disks.parse_synology(SECTION_TABLE)
    services = list(synology_disks.discover_synology_disks(section))
    assert {s.item for s in services} == {el[0] for el in SECTION_TABLE}


def make_section(
    state: int = 1,
    temperature: float = 42.1,
    disk: str = "none",
    model: str = "hello",
    role: str = "data",
    health: int = 1,
) -> synology_disks.Section:
    return {
        disk: synology_disks.Disk(
            state=state, temperature=temperature, disk=disk, model=model, role=role, health=health
        )
    }


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "state, expected",
    [(1, State.OK), (2, State.OK), (3, State.WARN), (4, State.CRIT), (5, State.CRIT)],
)
def test_result_state(state: int, expected: State) -> None:
    section = make_section(state=state)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))
    assert State.worst(*(r.state for r in result if isinstance(r, Result))) == expected


@pytest.mark.usefixtures("initialised_item_state")
def test_temperature_metric() -> None:
    temperature = 42.0
    section = make_section(temperature=temperature)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))[0]
    assert isinstance(result, Metric)
    assert result.value == temperature
    assert result.name == "temp"


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "role, expected",
    [("hotspare", State.OK), ("ssd_cache", State.OK), ("none", State.WARN), ("data", State.WARN)],
)
def test_check_role_is_ok_even_if_not_initialized(role: str, expected: State) -> None:
    section = make_section(role=role, state=3)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))
    assert State.worst(*(r.state for r in result if isinstance(r, Result))) == expected


@pytest.mark.usefixtures("initialised_item_state")
def test_disk_health_status(as_path: Callable[[str], Path]) -> None:
    parsed = get_parsed_snmp_section(synology_disks.snmp_section_synology_disks, as_path(DATA_0))
    assert parsed is not None
    assert list(synology_disks.check_synology_disks("Disk 3", {}, parsed)) == [
        Metric("temp", 26.0),
        Result(state=State.OK, summary="Temperature: 26.0 °C"),
        Result(state=State.OK, summary="Allocation status: OK"),
        Result(state=State.OK, summary="Model: HAT5300-8T"),
        Result(state=State.CRIT, summary="Health: Critical"),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_disk_health_status_missing(as_path: Callable[[str], Path]) -> None:
    parsed = get_parsed_snmp_section(synology_disks.snmp_section_synology_disks, as_path(DATA_1))
    assert parsed is not None
    assert list(synology_disks.check_synology_disks("Disk 1", {}, parsed)) == [
        Metric("temp", 27.0),
        Result(state=State.OK, summary="Temperature: 27.0 °C"),
        Result(state=State.OK, summary="Allocation status: OK"),
        Result(state=State.OK, summary="Model: HAT5300-8T"),
        Result(state=State.OK, summary="Health: Not provided (available with DSM 7.1 and above)"),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_hotspare(as_path: Callable[[str], Path]) -> None:
    parsed = get_parsed_snmp_section(synology_disks.snmp_section_synology_disks, as_path(DATA_2))
    assert parsed is not None
    assert list(synology_disks.check_synology_disks("Disk 4", {}, parsed)) == [
        Metric("temp", 35.0),
        Result(state=State.OK, summary="Temperature: 35.0 °C"),
        Result(state=State.OK, summary="Allocation status: disk is hotspare"),
        Result(state=State.OK, summary="Model: WD40000000-6666666"),
        Result(state=State.OK, summary="Health: Not provided (available with DSM 7.1 and above)"),
    ]
