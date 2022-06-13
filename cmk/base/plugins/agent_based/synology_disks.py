#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import synology, temperature


@dataclass(frozen=True)
class Disk:
    state: int
    temperature: float
    disk: str
    model: str

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Disk":
        return cls(disk=row[0], model=row[1], state=int(row[2]), temperature=float(row[3]))


Section = Mapping[str, Disk]


def parse_synology(string_table: StringTable) -> Section:
    return {row[0]: Disk.from_row(row) for row in string_table}


register.snmp_section(
    name="synology_disks",
    detect=synology.DETECT,
    parse_function=parse_synology,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.2.1.1",
        oids=[
            "2",  # SYNOLOGY-DISK-MIB::diskID
            "3",  # SYNOLOGY-DISK-MIB::diskModel
            "5",  # SYNOLOGY-DISK-MIB::diskStatus
            "6",  # SYNOLOGY-DISK-MIB::diskTemperature
        ],
    ),
)


def discover_synology_disks(section: Section) -> DiscoveryResult:
    for item, disk in section.items():
        # SSD and NVME used as cache are "not initialized". We remember that
        # here. TODO: Really true always in todays time and age?
        if (("SSD" in disk.model) or ("NVME" in disk.model)) and disk.state == 3:
            params = {"used_as_cache": True}
        else:
            params = {}
        yield Service(item=item, parameters=params)


def check_synology_disks(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    disk = section[item]
    yield from temperature.check_temperature(
        reading=disk.temperature,
        params=None,
        unique_name=item,
        value_store=get_value_store(),
    )

    states = {
        1: (State.OK, "OK"),
        2: (State.OK, "OK"),
        3: (State.WARN, "not initialized"),
        4: (State.CRIT, "system partition failed"),
        5: (State.CRIT, "crashed"),
    }
    state, text = states[disk.state]
    if disk.state == 3 and params.get("used_as_cache"):
        text = "used as cache"
        state = State.OK
    yield Result(
        state=state,
        summary=f"Status: {text}, Temperature: {disk.temperature} °C, Model: {disk.model}",
    )


register.check_plugin(
    name="synology_disks",
    sections=["synology_disks"],
    service_name="Disks %s",
    discovery_function=discover_synology_disks,
    check_function=check_synology_disks,
    check_default_parameters={},
)
