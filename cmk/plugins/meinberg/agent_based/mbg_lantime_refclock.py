#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

mbg_lantime_refclock_refmode_map = {
    "0": "notavailable",
    "1": "normalOperation",
    "2": "trackingSearching",
    "3": "antennaFaulty",
    "4": "warmBoot",
    "5": "coldBoot",
    "6": "antennaShortcircuit",
}

mbg_lantime_refclock_gpsstate_map = {
    "0": "not available",
    "1": "synchronized",
    "2": "not synchronized",
}


def discover_mbg_lantime_refclock(section: StringTable) -> DiscoveryResult:
    if len(section) > 0 and len(section[0]) == 6:
        yield Service()


def check_mbg_lantime_refclock(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not (section and len(section[0]) == 6):
        yield Result(state=State.UNKNOWN, summary="Got no state information")
        return

    ref_mode, gps_state, gps_pos, gps_sat_good, gps_sat_total, _gps_mode = section[0]

    # Handle the reported refclock mode
    if ref_mode in ("0", "3", "6"):
        refclock_state = State.CRIT
    elif ref_mode in ("2", "4", "5"):
        refclock_state = State.WARN
    else:
        refclock_state = State.OK
    yield Result(
        state=refclock_state,
        summary=f"Refclock State: {mbg_lantime_refclock_refmode_map.get(ref_mode, 'UNKNOWN')}",
    )

    # Handle gps state
    yield Result(
        state=State.CRIT if gps_state in ("0", "2") else State.OK,
        summary=f"GPS State: {mbg_lantime_refclock_gpsstate_map.get(gps_state, 'UNKNOWN')}",
    )

    # Add gps position
    if gps_pos:
        yield Result(state=State.OK, summary=gps_pos)

    # Handle number of satellites
    yield from check_levels(
        int(gps_sat_good),
        levels_lower=params["levels_lower"],
        metric_name="sat_good",
        render_func=lambda x: f"{int(x)}/{gps_sat_total}",
        label="Satellites",
    )
    yield Metric("sat_total", int(gps_sat_total))


def parse_mbg_lantime_refclock(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mbg_lantime_refclock = SimpleSNMPSection(
    name="mbg_lantime_refclock",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5597.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.3.2",
        oids=["4", "6", "7", "9", "10", "16"],
    ),
    parse_function=parse_mbg_lantime_refclock,
)


check_plugin_mbg_lantime_refclock = CheckPlugin(
    name="mbg_lantime_refclock",
    service_name="LANTIME Refclock",
    discovery_function=discover_mbg_lantime_refclock,
    check_function=check_mbg_lantime_refclock,
    check_default_parameters={
        "levels_lower": ("fixed", (3, 3)),
    },
)
