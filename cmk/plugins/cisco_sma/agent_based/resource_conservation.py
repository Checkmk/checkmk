#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from enum import Enum

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

from .detect import DETECT_CISCO_SMA


class ResourceConservation(Enum):
    UNKNOWN = -999
    OFF = 1
    MEMORY_SHORTAGE = 2
    QUEUE_SPACE_SHORTAGE = 3
    QUEUE_FULL = 4


def _check_resource_conservation(section: ResourceConservation | None) -> CheckResult:
    match section:
        case ResourceConservation.OFF:
            summary = "Resource conservation mode off"
            state = State.OK
        case ResourceConservation.MEMORY_SHORTAGE:
            summary = "Resource conservation mode on (memory shortage)"
            state = State.WARN
        case ResourceConservation.QUEUE_SPACE_SHORTAGE:
            summary = "Resource conservation mode on (queue space shortage)"
            state = State.WARN
        case ResourceConservation.QUEUE_FULL:
            summary = "Resource conservation mode on (queue full)"
            state = State.CRIT
        case _:
            summary = "Resource conservation status unknown"
            state = State.UNKNOWN
    yield Result(state=state, summary=summary)


def _discover_resource_conservation(section: ResourceConservation | None) -> DiscoveryResult:
    yield Service()


def _parse_resource_conservation(string_table: StringTable) -> ResourceConservation | None:
    if not string_table or not string_table[0]:
        return None

    try:
        return ResourceConservation(int(string_table[0][0]))
    except ValueError:
        # We were likely given some value that we don't know how to understand.
        return ResourceConservation.UNKNOWN


snmp_section_resource_conservation = SimpleSNMPSection(
    parsed_section_name="cisco_sma_resource_conservation",
    name="cisco_sma_resource_conservation",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["6"],
    ),
    parse_function=_parse_resource_conservation,
)


check_plugin_resource_conservation = CheckPlugin(
    name="cisco_sma_resource_conservation",
    service_name="Resource conservation",
    discovery_function=_discover_resource_conservation,
    check_function=_check_resource_conservation,
)
