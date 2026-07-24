#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.qnap.lib import DETECT_QNAP


def discover_qnap_disks(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=x[0]) for x in section if x[2] != "-5")


def check_qnap_disks(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "0": (State.OK, "ready"),
        "-4": (State.CRIT, "unknown"),
        "-5": (State.CRIT, "no disk"),
        "-6": (State.CRIT, "invalid"),
        "-9": (State.CRIT, "read write error"),
    }

    for desc, temp, status, model, size, cond in section:
        if desc == item:
            state, state_readable = map_states.get(status, (State.UNKNOWN, "unknown"))
            yield Result(state=state, summary=f"Status: {state_readable} ({cond})")

            if "--" in cond:
                yield Result(state=State.WARN, summary="SMART Information missing")
            elif cond != "GOOD":
                yield Result(state=State.WARN, summary="SMART Warnings")

            yield Result(
                state=State.OK, summary=f"Model: {model}, Temperature: {temp}, Size: {size}"
            )


def parse_qnap_disks(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_qnap_disks = SimpleSNMPSection(
    name="qnap_disks",
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.11.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_qnap_disks,
)


check_plugin_qnap_disks = CheckPlugin(
    name="qnap_disks",
    service_name="Disk %s",
    discovery_function=discover_qnap_disks,
    check_function=check_qnap_disks,
)
