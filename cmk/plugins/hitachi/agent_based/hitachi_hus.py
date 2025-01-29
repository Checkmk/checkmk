#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

# For Hitachi Unified Storage (HUS) devices which support the USPMIB
# This devices has two units: Disk Controller (DKC) and Disk Unit (DKC)

# Example output from DKC:
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.3 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.4 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.5 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.6 5
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.7 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.8 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.9 1

# Example output from DKU:
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.3 4
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.4 3
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.5 1


@dataclass(frozen=True)
class PropertyState:
    label: str
    state: State
    description: str


Section = Mapping[str, Sequence[PropertyState]]


_DETECT_HUS = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "hm700"),
    contains(".1.3.6.1.2.1.1.1.0", "hm800"),
    contains(".1.3.6.1.2.1.1.1.0", "hm850"),
    contains(".1.3.6.1.2.1.1.1.0", "hm900"),
)


_HUS_MAP_STATES = {
    "0": (State.UNKNOWN, "unknown"),
    "1": (State.OK, "no error"),
    "2": (State.CRIT, "acute"),
    "3": (State.CRIT, "serious"),
    "4": (State.WARN, "moderate"),
    "5": (State.WARN, "service"),
}


def parse_hitachi_hus_dkc(string_table: StringTable) -> Section:
    labels = (
        "Processor",
        "Internal Bus",
        "Cache",
        "Shared Memory",
        "Power Supply",
        "Battery",
        "Fan",
        "Environment",
    )

    return {
        item: tuple(
            PropertyState(l, *_HUS_MAP_STATES[v]) for l, v in zip(labels, rest, strict=True)
        )
        for item, *rest in string_table
    }


def parse_hitachi_hus_dku(string_table: StringTable) -> Section:
    labels = ("Power Supply", "Fan", "Environment", "Drive")

    return {
        item: tuple(
            PropertyState(l, *_HUS_MAP_STATES[v]) for l, v in zip(labels, rest, strict=True)
        )
        for item, *rest in string_table
    }


def inventory_hitachi_hus(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_hitachi_hus(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    for prop in data:
        yield Result(state=prop.state, summary=f"{prop.label}: {prop.description}")


snmp_section_hitachi_hus_dkc = SimpleSNMPSection(
    name="hitachi_hus_dkc",
    detect=_DETECT_HUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.6.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
    parse_function=parse_hitachi_hus_dkc,
)


check_plugin_hitachi_hus_dkc = CheckPlugin(
    name="hitachi_hus_dkc",
    service_name="HUS DKC Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)


snmp_section_hitachi_hus_dku = SimpleSNMPSection(
    name="hitachi_hus_dku",
    detect=_DETECT_HUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.7.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    parse_function=parse_hitachi_hus_dku,
)


check_plugin_hitachi_hus_dku = CheckPlugin(
    name="hitachi_hus_dku",
    service_name="HUS DKU Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)
