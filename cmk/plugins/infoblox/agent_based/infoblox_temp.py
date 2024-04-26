#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.infoblox import DETECT_INFOBLOX
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.sys-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 CPU_TEMP: +36.00 C --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 No temperature information available. --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 SYS_TEMP: +34.00 C --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.sys-temp

# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.sys-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.sys-temp

# Suggested by customer


@dataclass(frozen=True)
class TempDescr:
    state: tuple[int, str]
    reading: float
    unit: str


Section = Mapping[str, TempDescr]


def _parse_infoblox_temp(state_table: Sequence[str], temp_table: Sequence[str]) -> Section:
    map_states = {
        "1": (0, "working"),
        "2": (1, "warning"),
        "3": (2, "failed"),
        "4": (1, "inactive"),
        "5": (3, "unknown"),
    }

    parsed: dict[str, TempDescr] = {}
    # Just for a better handling
    for index, state, descr in list(zip(["1", "2", ""], state_table, temp_table)):
        if ":" not in descr:
            continue

        name, val_str = descr.split(":", 1)
        r_val, unit = val_str.split()
        val = float(r_val)

        what_name = f"{name} {index}"
        parsed.setdefault(
            what_name.strip(),
            TempDescr(state=map_states[state], reading=val, unit=unit.lower()),
        )

    return parsed


def parse_infoblox_temp(string_table: Sequence[StringTable]) -> Section:
    if not all(string_table):
        return {}

    version_raw = string_table[0][0][1].split(".")
    major_version = int(version_raw[0])
    minor_version = int(version_raw[1])

    if major_version > 8 or (major_version == 8 and minor_version > 6):
        return _parse_infoblox_temp(string_table[1][0][1:4], string_table[2][0][1:4])
    return _parse_infoblox_temp(string_table[1][0][3:], string_table[2][0][3:])


snmp_section_infoblox_temp = SNMPSection(
    name="infoblox_temp",
    detect=DETECT_INFOBLOX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.7",
            oids=[OIDEnd(), "0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2",
            oids=[OIDEnd(), "37", "38", "39", "40", "41"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3",
            oids=[OIDEnd(), "37", "38", "39", "40", "41"],
        ),
    ],
    parse_function=parse_infoblox_temp,
)


def discover_infoblox_temp(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_temp(
    item: str, params: TempParamType, section: Section, value_store: MutableMapping[str, Any]
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    devstate, devstatename = sensor.state
    yield from check_temperature(
        sensor.reading,
        params,
        unique_name=f"infoblox_cpu_temp_{item}",
        value_store=value_store,
        dev_status=devstate,
        dev_status_name=devstatename,
        dev_unit=sensor.unit,
    )


def check_infoblox_temp(item: str, params: None, section: Section) -> CheckResult:
    yield from check_temp(item, params, section, get_value_store())


check_plugin_infoblox_temp = CheckPlugin(
    name="infoblox_temp",
    service_name="Temperature %s",
    discovery_function=discover_infoblox_temp,
    check_function=check_infoblox_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
