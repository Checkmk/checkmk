#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

# The typical OSN power unit delivers 750 W max


class HuaweiOsnPowerParams(TypedDict):
    levels: tuple[int, int]


def discover_huawei_osn_power(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_huawei_osn_power(
    item: str, params: HuaweiOsnPowerParams, section: StringTable
) -> CheckResult:
    for line in section:
        if item == line[0]:
            reading = int(line[1])
            yield from check_levels(
                reading,
                levels_upper=("fixed", params["levels"]),
                metric_name="power",
                label="Current reading",
                render_func=lambda v: f"{int(v)} W",
            )


def parse_huawei_osn_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_huawei_osn_power = SimpleSNMPSection(
    name="huawei_osn_power",
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.4.70.20.20.10.1",
        oids=["1", "2"],
    ),
    parse_function=parse_huawei_osn_power,
)


check_plugin_huawei_osn_power = CheckPlugin(
    name="huawei_osn_power",
    service_name="Unit %s (Power)",
    discovery_function=discover_huawei_osn_power,
    check_function=check_huawei_osn_power,
    check_default_parameters={
        "levels": (700, 730),
    },
)
