#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import synology_disks
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

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


@pytest.mark.parametrize(
    "state, expected",
    [(1, State.OK), (2, State.OK), (3, State.WARN), (4, State.CRIT), (5, State.CRIT)],
)
def test_result_state(state: int, expected: State) -> None:
    section = make_section(state=state)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))
    assert State.worst(*(r.state for r in result if isinstance(r, Result))) == expected


def test_temperature_metric() -> None:
    temperature = 42.0
    section = make_section(temperature=temperature)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))[0]
    assert isinstance(result, Metric)
    assert result.value == temperature
    assert result.name == "temp"


@pytest.mark.parametrize(
    "role, expected",
    [("hotspare", State.OK), ("ssd_cache", State.OK), ("none", State.WARN), ("data", State.WARN)],
)
def test_check_role_is_ok_even_if_not_initialized(role: str, expected: State) -> None:
    section = make_section(role=role, state=3)
    item = list(section.keys())[0]
    result = list(synology_disks.check_synology_disks(item=item, section=section, params={}))
    assert State.worst(*(r.state for r in result if isinstance(r, Result))) == expected
