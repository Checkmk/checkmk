#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.meinberg.liblantime import (
    check_mbg_lantime_state_common,
    DETECT_MBG_LANTIME_NG,
    MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)


def discover_mbg_lantime_ng_state(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_mbg_lantime_ng_state(
    params: Mapping[str, tuple[float, float]], section: StringTable
) -> CheckResult:
    states = {
        "0": (State.CRIT, "not available"),
        "1": (State.CRIT, "not synchronized"),
        "2": (State.OK, "synchronized"),
    }
    ntp_state, stratum, refclock_name, refclock_offset_str = section[0]
    # Convert from milliseconds to microseconds
    # make sure, we don't try to parse "n/a" but pass it on, because
    # check_mbg_lantime_state_common() also tries to parse it as float
    refclock_offset = (
        refclock_offset_str
        if refclock_offset_str == "n/a"
        else float(refclock_offset_str.lstrip("=")) * 1000
    )
    yield from check_mbg_lantime_state_common(
        states,
        params["stratum"],
        params["offset"],
        ntp_state,
        stratum,
        refclock_name.lstrip("="),
        refclock_offset,
    )


def parse_mbg_lantime_ng_state(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mbg_lantime_ng_state = SimpleSNMPSection(
    name="mbg_lantime_ng_state",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.2",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_mbg_lantime_ng_state,
)


check_plugin_mbg_lantime_ng_state = CheckPlugin(
    name="mbg_lantime_ng_state",
    service_name="LANTIME State",
    discovery_function=discover_mbg_lantime_ng_state,
    check_function=check_mbg_lantime_ng_state,
    check_ruleset_name="mbg_lantime_state",
    check_default_parameters=MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)
