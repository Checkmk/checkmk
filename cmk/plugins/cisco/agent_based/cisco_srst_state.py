#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import timedelta

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

# .1.3.6.1.4.1.9.9.441.1.3.1 CISCO-SRST-MIB::csrstState (1: active, 2: inactive)
# .1.3.6.1.4.1.9.9.441.1.3.4 CISCO-SRST-MIB::csrstTotalUpTime


def discover_cisco_srst_state(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_cisco_srst_state(section: StringTable) -> CheckResult:
    srst_state, uptime_text = section[0]

    # Check the state
    if srst_state == "1":
        yield Result(state=State.CRIT, summary="SRST active")
    else:
        yield Result(state=State.OK, summary="SRST inactive")

    # Display SRST uptime
    uptime_sec = int(uptime_text) * 60
    yield from check_levels(
        uptime_sec,
        "uptime",
        None,
        human_readable_func=lambda x: timedelta(seconds=int(x)),
        infoname=f"Up since {time.strftime('%c', time.localtime(time.time() - uptime_sec))}, uptime",
    )


def parse_cisco_srst_state(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cisco_srst_state = SimpleSNMPSection(
    name="cisco_srst_state",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), equals(".1.3.6.1.4.1.9.9.441.1.2.1.0", "1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.441.1.3",
        oids=["1", "4"],
    ),
    parse_function=parse_cisco_srst_state,
)


check_plugin_cisco_srst_state = CheckPlugin(
    name="cisco_srst_state",
    service_name="SRST State",
    discovery_function=discover_cisco_srst_state,
    check_function=check_cisco_srst_state,
)
