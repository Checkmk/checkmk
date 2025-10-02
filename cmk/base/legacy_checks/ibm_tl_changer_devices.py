#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.base.check_legacy_includes.ibm_tape_library import ibm_tape_library_get_device_state

# .1.3.6.1.4.1.14851.3.1.11.2.1.4.1 Logical_Library: 1 --> SNIA-SML-MIB::changerDevice-ElementName.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.4.2 Logical_Library: LTO6 --> SNIA-SML-MIB::changerDevice-ElementName.2
# .1.3.6.1.4.1.14851.3.1.11.2.1.8.1 3 --> SNIA-SML-MIB::changerDevice-Availability.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.8.2 3 --> SNIA-SML-MIB::changerDevice-Availability.2
# .1.3.6.1.4.1.14851.3.1.11.2.1.9.1 2 --> SNIA-SML-MIB::changerDevice-OperationalStatus.1
# .1.3.6.1.4.1.14851.3.1.11.2.1.9.2 2 --> SNIA-SML-MIB::changerDevice-OperationalStatus.2


@dataclass(frozen=True)
class Device:
    avail: str
    status: str


type Section = Mapping[str, Device]


def _make_item(name: str) -> str:
    return name.replace("Logical_Library:", "").strip()


def parse_ibm_tl_changer_devices(string_table: StringTable) -> Section:
    return {
        _make_item(name): Device(avail=avail, status=status) for name, avail, status in string_table
    }


def inventory_ibm_tl_changer_devices(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_ibm_tl_changer_devices(item: str, section: Section) -> CheckResult:
    if (device := section.get(item)) is None:
        return
    yield from ibm_tape_library_get_device_state(device.avail, device.status)


snmp_section_ibm_tl_changer_devices = SimpleSNMPSection(
    name="ibm_tl_changer_devices",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.32925.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2.6.254"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14851.3.1.11.2.1",
        oids=["4", "8", "9"],
    ),
    parse_function=parse_ibm_tl_changer_devices,
)


check_plugin_ibm_tl_changer_devices = CheckPlugin(
    name="ibm_tl_changer_devices",
    service_name="Changer device %s",
    discovery_function=inventory_ibm_tl_changer_devices,
    check_function=check_ibm_tl_changer_devices,
)
