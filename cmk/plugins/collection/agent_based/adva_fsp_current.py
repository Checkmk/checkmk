#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.1.101318912  8110
# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.2.101318912  65600
# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.3.101318912  9
# .1.3.6.1.4.1.2544.2.5.5.1.1.1.101318912  "PSU/7HU-AC-800"
# .1.3.6.1.4.1.2544.2.5.5.1.1.5.101318912  "MOD-1-1"

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


@dataclass(frozen=True)
class SensorData:
    name: str
    crit: float
    current: float


Section = Mapping[str, SensorData]


def parse_adva_fsp_current(string_table: StringTable) -> Section:
    return {
        index_aid: SensorData(
            name=unit_name,
            crit=float(upper_threshold_str) / 1000.0,
            current=float(current_str) / 1000.0,
        )
        for current_str, upper_threshold_str, power_str, unit_name, index_aid in string_table
        # Ignore non-connected sensors
        if index_aid and power_str
    }


snmp_section_adva_fsp_current = SimpleSNMPSection(
    name="adva_fsp_current",
    detect=equals(".1.3.6.1.2.1.1.1.0", "Fiber Service Platform F7"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2544",
        oids=[
            "1.11.2.4.2.2.1.1",
            "1.11.2.4.2.2.1.2",
            "1.11.2.4.2.2.1.3",
            "2.5.5.1.1.1",
            "2.5.5.2.1.5",
        ],
    ),
    parse_function=parse_adva_fsp_current,
)


def discover_adva_fsp_current(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_adva_fsp_current(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    yield from check_levels(
        sensor.current,
        metric_name="current",
        levels_upper=("fixed", (sensor.crit, sensor.crit)),
        render_func=lambda x: f"{x:.3f} A",
        label=f"[{sensor.name}]",
    )


check_plugin_adva_fsp_current = CheckPlugin(
    name="adva_fsp_current",
    service_name="Power Supply %s",
    discovery_function=discover_adva_fsp_current,
    check_function=check_adva_fsp_current,
)
