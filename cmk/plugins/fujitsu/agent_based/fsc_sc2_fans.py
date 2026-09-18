#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2
from cmk.plugins.lib.fan import check_fan

_STATUS_MAP = {
    "1": (State.UNKNOWN, "Status is unknown"),
    "2": (State.OK, "Status is disabled"),
    "3": (State.OK, "Status is ok"),
    "4": (State.CRIT, "Status is failed"),
    "5": (State.WARN, "Status is prefailure-predicted"),
    "6": (State.WARN, "Status is redundant-fan-failed"),
    "7": (State.UNKNOWN, "Status is not-manageable"),
    "8": (State.OK, "Status is not-present"),
}


def parse_fsc_sc2_fans(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.1 "FAN1 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.2 "FAN2 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.3 "FAN3 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.4 "FAN4 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.5 "FAN5 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.6 "FAN PSU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.7 "FAN PSU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.2 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.3 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.4 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.5 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.6 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.7 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.1 5820
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.2 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.3 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.4 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.5 6120
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.6 2400
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.7 2400


def discover_fsc_sc2_fans(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] != "8":
            yield Service(item=line[0])


def check_fsc_sc2_fans(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for designation, status, rpm in section:
        if designation == item:
            state, state_readable = _STATUS_MAP.get(status, (State.UNKNOWN, "Status is unknown"))
            yield Result(state=state, summary=state_readable)
            if rpm:
                yield from check_fan(int(rpm), params)
            else:
                yield Result(state=State.OK, summary="Device did not deliver RPM values")


snmp_section_fsc_sc2_fans = SimpleSNMPSection(
    name="fsc_sc2_fans",
    parse_function=parse_fsc_sc2_fans,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.5.2.1",
        oids=["3", "5", "6"],
    ),
)


check_plugin_fsc_sc2_fans = CheckPlugin(
    name="fsc_sc2_fans",
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_fans,
    check_function=check_fsc_sc2_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1500, 2000),
    },
)
