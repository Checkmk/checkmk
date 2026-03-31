#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

# The dBm should not get too low. So we check only for lower levels


class HuaweiOsnLaserParams(TypedDict, total=False):
    levels_low_in: tuple[int, int]
    levels_low_out: tuple[int, int]


def discover_huawei_osn_laser(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_huawei_osn_laser(
    item: str, params: HuaweiOsnLaserParams, section: StringTable
) -> CheckResult:
    for line in section:
        if item == line[0]:
            dbm_in = float(line[2]) / 10
            dbm_out = float(line[1]) / 10

            # In
            yield from check_levels(
                dbm_in,
                levels_lower=params.get("levels_low_in"),
                metric_name="input_signal_power_dBm",
                label="In",
                render_func=lambda v: f"{v:.1f} dBm",
            )

            # And out
            yield from check_levels(
                dbm_out,
                levels_lower=params.get("levels_low_out"),
                metric_name="output_signal_power_dBm",
                label="Out",
                render_func=lambda v: f"{v:.1f} dBm",
            )

            # FEC Correction
            fec_before = line[3]
            fec_after = line[4]
            if fec_before != "" and fec_after != "":
                yield Result(
                    state=State.OK, summary=f"FEC Correction before/after: {fec_before}/{fec_after}"
                )


def parse_huawei_osn_laser(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_huawei_osn_laser = SimpleSNMPSection(
    name="huawei_osn_laser",
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.3.40.50.119.10.1",
        oids=["6.200", "2.200", "2.203", "2.252", "2.253"],
    ),
    parse_function=parse_huawei_osn_laser,
)


check_plugin_huawei_osn_laser = CheckPlugin(
    name="huawei_osn_laser",
    service_name="Laser %s",
    discovery_function=discover_huawei_osn_laser,
    check_function=check_huawei_osn_laser,
    check_ruleset_name="huawei_osn_laser",
    check_default_parameters={
        "levels_low_in": (-160, -180),
        "levels_low_out": (-35, -40),
    },
)
