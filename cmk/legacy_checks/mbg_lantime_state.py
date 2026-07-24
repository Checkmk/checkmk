#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    not_exists,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.meinberg.liblantime import (
    check_mbg_lantime_state_common,
    MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)


def discover_mbg_lantime_state(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_mbg_lantime_state(
    params: Mapping[str, tuple[float, float]], section: StringTable
) -> CheckResult:
    states = {
        "0": (State.CRIT, "not synchronized"),
        "1": (State.CRIT, "no good reference clock"),
        "2": (State.OK, "sync to external reference clock"),
        "3": (State.OK, "sync to serial reference clock"),
        "4": (State.OK, "normal operation PPS"),
        "5": (State.OK, "normal operation reference clock"),
    }
    ntp_state, stratum, refclock_name, refclock_offset = section[0]
    yield from check_mbg_lantime_state_common(
        states,
        params["stratum"],
        params["offset"],
        ntp_state,
        stratum,
        refclock_name,
        refclock_offset,
    )


def parse_mbg_lantime_state(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mbg_lantime_state = SimpleSNMPSection(
    name="mbg_lantime_state",
    detect=all_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5597.3"),
        not_exists(".1.3.6.1.4.1.5597.30.0.2.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.3.1",
        oids=["2", "3", "5", "7"],
    ),
    parse_function=parse_mbg_lantime_state,
)


check_plugin_mbg_lantime_state = CheckPlugin(
    name="mbg_lantime_state",
    service_name="LANTIME State",
    discovery_function=discover_mbg_lantime_state,
    check_function=check_mbg_lantime_state,
    check_ruleset_name="mbg_lantime_state",
    check_default_parameters=MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)
