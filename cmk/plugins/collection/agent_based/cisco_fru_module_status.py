#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    OIDCached,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.entity_mib import PhysicalClasses

# .1.3.6.1.2.1.47.1.1.1.1.2.1   "CISCO1921/K9 chassis" --> ENTITY-MIB::entPhysicalDescr.1
# .1.3.6.1.2.1.47.1.1.1.1.2.2   "C1921 Chassis Slot" --> ENTITY-MIB::entPhysicalDescr.2
# .1.3.6.1.2.1.47.1.1.1.1.2.3   "C1921 Mother board 2GE, integrated VPN and 2W" --> ENTITY-MIB::entPhysicalDescr.3
# .1.3.6.1.2.1.47.1.1.1.1.2.4   "C1921 DaughterCard Slot" --> ENTITY-MIB::entPhysicalDescr.4
# .1.3.6.1.2.1.47.1.1.1.1.2.5   "ADSL/VDSL over POTS supporting ADSL1, ADSL2, ADSL2+ and VDSL2" --> ENTITY-MIB::entPhysicalDescr.5
# .1.3.6.1.2.1.47.1.1.1.1.2.6   "MPC ATMSAR" --> ENTITY-MIB::entPhysicalDescr.6
# .1.3.6.1.2.1.47.1.1.1.1.2.7   "VDSL_ETHERNET" --> ENTITY-MIB::entPhysicalDescr.7
# .1.3.6.1.2.1.47.1.1.1.1.2.8   "C1921 DaughterCard Slot" --> ENTITY-MIB::entPhysicalDescr.8
# .1.3.6.1.2.1.47.1.1.1.1.2.9   "C1921 ISM Slot" --> ENTITY-MIB::entPhysicalDescr.9
# .1.3.6.1.2.1.47.1.1.1.1.2.10  "Embedded Service Engine" --> ENTITY-MIB::entPhysicalDescr.10
# .1.3.6.1.2.1.47.1.1.1.1.2.11  "CN Gigabit Ethernet" --> ENTITY-MIB::entPhysicalDescr.11
# .1.3.6.1.2.1.47.1.1.1.1.2.12  "CN Gigabit Ethernet" --> ENTITY-MIB::entPhysicalDescr.12
# .1.3.6.1.2.1.47.1.1.1.1.2.13  "Container of powerSupply Containers" --> ENTITY-MIB::entPhysicalDescr.13
# .1.3.6.1.2.1.47.1.1.1.1.2.14  "Container of Power Supply" --> ENTITY-MIB::entPhysicalDescr.14
# .1.3.6.1.2.1.47.1.1.1.1.2.15  "" --> ENTITY-MIB::entPhysicalDescr.15
# .1.3.6.1.2.1.47.1.1.1.1.5.1   3  --> ENTITY-MIB::entPhysicalClass.1
# .1.3.6.1.2.1.47.1.1.1.1.5.2   5  --> ENTITY-MIB::entPhysicalClass.2
# .1.3.6.1.2.1.47.1.1.1.1.5.3   9  --> ENTITY-MIB::entPhysicalClass.3
# .1.3.6.1.2.1.47.1.1.1.1.5.4   5  --> ENTITY-MIB::entPhysicalClass.4
# .1.3.6.1.2.1.47.1.1.1.1.5.5   9  --> ENTITY-MIB::entPhysicalClass.5
# .1.3.6.1.2.1.47.1.1.1.1.5.6   10 --> ENTITY-MIB::entPhysicalClass.6
# .1.3.6.1.2.1.47.1.1.1.1.5.7   10 --> ENTITY-MIB::entPhysicalClass.7
# .1.3.6.1.2.1.47.1.1.1.1.5.8   5  --> ENTITY-MIB::entPhysicalClass.8
# .1.3.6.1.2.1.47.1.1.1.1.5.9   5  --> ENTITY-MIB::entPhysicalClass.9
# .1.3.6.1.2.1.47.1.1.1.1.5.10  10 --> ENTITY-MIB::entPhysicalClass.10
# .1.3.6.1.2.1.47.1.1.1.1.5.11  10 --> ENTITY-MIB::entPhysicalClass.11
# .1.3.6.1.2.1.47.1.1.1.1.5.12  10 --> ENTITY-MIB::entPhysicalClass.12
# .1.3.6.1.2.1.47.1.1.1.1.5.13  5  --> ENTITY-MIB::entPhysicalClass.13
# .1.3.6.1.2.1.47.1.1.1.1.5.14  5  --> ENTITY-MIB::entPhysicalClass.14
# .1.3.6.1.2.1.47.1.1.1.1.5.15  6  --> ENTITY-MIB::entPhysicalClass.15
# .1.3.6.1.2.1.47.1.1.1.1.7.1   "CISCO1921/K9 chassis" --> ENTITY-MIB::entPhysicalName.1
# .1.3.6.1.2.1.47.1.1.1.1.7.2   "C1921 Chassis Slot 0" --> ENTITY-MIB::entPhysicalName.2
# .1.3.6.1.2.1.47.1.1.1.1.7.3   "C1921 Mother board 2GE, integrated VPN and 2W on Slot 0" --> ENTITY-MIB::entPhysicalName.3
# .1.3.6.1.2.1.47.1.1.1.1.7.4   "DaughterCard Slot 0 on Card 0" --> ENTITY-MIB::entPhysicalName.4
# .1.3.6.1.2.1.47.1.1.1.1.7.5   "ADSL/VDSL over POTS supporting ADSL1, ADSL2, ADSL2+ and VDSL2 on Slot 0 SubSlot 0" --> ENTITY-MIB::entPhysicalName.5
# .1.3.6.1.2.1.47.1.1.1.1.7.6   "ATM0/0/0" --> ENTITY-MIB::entPhysicalName.6
# .1.3.6.1.2.1.47.1.1.1.1.7.7   "Ethernet0/0/0" --> ENTITY-MIB::entPhysicalName.7
# .1.3.6.1.2.1.47.1.1.1.1.7.8   "DaughterCard Slot 1 on Card 0" --> ENTITY-MIB::entPhysicalName.8
# .1.3.6.1.2.1.47.1.1.1.1.7.9   "C1921 ISM Slot 0" --> ENTITY-MIB::entPhysicalName.9
# .1.3.6.1.2.1.47.1.1.1.1.7.10  "Embedded-Service-Engine0/0" --> ENTITY-MIB::entPhysicalName.10
# .1.3.6.1.2.1.47.1.1.1.1.7.11  "GigabitEthernet0/0" --> ENTITY-MIB::entPhysicalName.11
# .1.3.6.1.2.1.47.1.1.1.1.7.12  "GigabitEthernet0/1" --> ENTITY-MIB::entPhysicalName.12
# .1.3.6.1.2.1.47.1.1.1.1.7.13  "Container of powerSupply Containers" --> ENTITY-MIB::entPhysicalName.13
# .1.3.6.1.2.1.47.1.1.1.1.7.14  "Container of Power Supply" --> ENTITY-MIB::entPhysicalName.14
# .1.3.6.1.2.1.47.1.1.1.1.7.15  "" --> ENTITY-MIB::entPhysicalName.15

# .1.3.6.1.4.1.9.9.117.1.2.1.1.2.5  2 --> CISCO-ENTITY-FRU-CONTROL-MIB::cefcModuleOperStatus.5


@dataclasses.dataclass(frozen=True)
class Module:
    state: str
    name: str

    _STATE_MAP = {
        "1": (State.CRIT, "unknown"),
        "2": (State.OK, "OK"),
        "3": (State.WARN, "disabled"),
        "4": (State.WARN, "OK but diag failed"),
        "5": (State.WARN, "boot"),
        "6": (State.WARN, "self test"),
        "7": (State.CRIT, "failed"),
        "8": (State.CRIT, "missing"),
        "9": (State.CRIT, "mismatch with parent"),
        "10": (State.CRIT, "mismatch config"),
        "11": (State.CRIT, "diag failed"),
        "12": (State.CRIT, "dormant"),
        "13": (State.CRIT, "out of service (admin)"),
        "14": (State.CRIT, "out of service (temperature)"),
        "15": (State.CRIT, "powered down"),
        "16": (State.WARN, "powered up"),
        "17": (State.CRIT, "power denied"),
        "18": (State.WARN, "power cycled"),
        "19": (State.WARN, "OK but power over warning"),
        "20": (State.WARN, "OK but power over critical"),
        "21": (State.WARN, "sync in progress"),
        "22": (State.WARN, "upgrading"),
        "23": (State.WARN, "OK but auth failed"),
        "24": (State.WARN, "minimum disruptive restart upgrade"),
        "25": (State.WARN, "firmware mismatch found"),
        "26": (State.WARN, "firmware download success"),
        "27": (State.CRIT, "firmware download failure"),
    }

    @property
    def monitoring_state(self) -> State:
        return self._STATE_MAP[self.state][0]

    @property
    def human_readable_state(self) -> str:
        return self._STATE_MAP[self.state][1]


Section = Mapping[str, Module]


def parse(string_table: Sequence[StringTable]) -> Section:
    collected_entities: dict[str, str] = {}
    for oid, hardware_type, hardware_name in string_table[0]:
        if PhysicalClasses.parse_cisco(hardware_type) is PhysicalClasses.module:
            collected_entities.setdefault(oid, hardware_name)
    return {
        oid: Module(
            state=module_state,
            name=collected_entities[oid],
        )
        for oid, module_state in string_table[1]
        if oid in collected_entities
    }


snmp_section_cisco_fru_module_status = SNMPSection(
    name="cisco_fru_module_status",
    parse_function=parse,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        exists(".1.3.6.1.4.1.9.9.117.1.*"),
    ),
    fetch=[
        SNMPTree(
            ".1.3.6.1.2.1.47.1.1.1.1",
            [
                OIDEnd(),
                "5",  # entPhysicalClass
                OIDCached("7"),  # entPhysicalName
            ],
        ),
        SNMPTree(
            ".1.3.6.1.4.1.9.9.117.1.2.1.1",
            [
                OIDEnd(),
                "2",  # cefcModuleOperStatus
            ],
        ),
    ],
)


def inventory_cisco_fru_module_status(section: Section) -> DiscoveryResult:
    for module_index in section:
        yield Service(item=module_index)


def check_cisco_fru_module_status(item: str, section: Section) -> CheckResult:
    if (module := section.get(item)) is None:
        return
    yield Result(
        state=module.monitoring_state,
        summary=f"{f'[{module.name}] ' if module.name else ''}Operational status: {module.human_readable_state}",
    )


check_plugin_cisco_fru_module_status = CheckPlugin(
    name="cisco_fru_module_status",
    service_name="FRU Module Status %s",
    discovery_function=inventory_cisco_fru_module_status,
    check_function=check_cisco_fru_module_status,
)
