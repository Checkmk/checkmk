#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    exists,
    get_value_store,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import temperature


@dataclass(frozen=True)
class Disk:
    state: int
    temperature: float
    disk: str
    model: str
    health: Union[int, None]

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Disk":
        health = int(health_raw) if (health_raw := row[4]) != "" else None
        return cls(
            disk=row[0], model=row[1], state=int(row[2]), temperature=float(row[3]), health=health
        )


Section = Mapping[str, Disk]


def parse_synology(string_table: StringTable) -> Section:
    return {row[0]: Disk.from_row(row) for row in string_table}


register.snmp_section(
    name="synology_disks",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Linux"),
        exists(".1.3.6.1.4.1.6574.*"),
    ),
    parse_function=parse_synology,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.2.1.1",
        oids=[
            "2",  # SYNOLOGY-DISK-MIB::diskID
            "3",  # SYNOLOGY-DISK-MIB::diskModel
            "5",  # SYNOLOGY-DISK-MIB::diskStatus
            "6",  # SYNOLOGY-DISK-MIB::diskTemperature
            "13",  # diskHealthStatus (available from DSM 7.1. and above)
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
    temperature_result = list(
        temperature.check_temperature(
            reading=disk.temperature,
            params={
                "device_levels_handling": "usr",
            },
            unique_name=item,
            value_store=get_value_store(),
        )
    )
    yield from temperature_result[:2]  # ignore statement about level matching set to "usr"

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
    yield Result(state=state, summary=f"Allocation status: {text}")
    yield Result(state=State.OK, summary=f"Model: {disk.model}")

    health_states = {
        1: (State.OK, "Normal"),
        2: (State.WARN, "Warning"),
        3: (State.CRIT, "Critical"),
        4: (State.CRIT, "Failing"),
        None: (State.OK, "Not provided (available with DSM 7.1 and above)"),
    }
    health_state, health_text = health_states[disk.health]
    yield Result(state=health_state, summary=f"Health: {health_text}")


register.check_plugin(
    name="synology_disks",
    sections=["synology_disks"],
    service_name="Disks %s",
    discovery_function=discover_synology_disks,
    check_function=check_synology_disks,
    check_default_parameters={},
)
