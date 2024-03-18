#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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

from .lib import DETECT_PEAKFLOW_TMS


def parse_peakflow_tms_updates(string_table: StringTable) -> Mapping[str, str] | None:
    return (
        {"Device": string_table[0][0], "Mitigation": string_table[0][1]} if string_table else None
    )


snmp_section_arbor_peakflow_tms_updates = SimpleSNMPSection(
    name="arbor_peakflow_tms_updates",
    detect=DETECT_PEAKFLOW_TMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.5",
        oids=["1.2.0", "2.1.0"],
    ),
    parse_function=parse_peakflow_tms_updates,
)


def inventory_peakflow_tms_updates(section: Mapping[str, str]) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_peakflow_tms_updates(item: str, section: Mapping[str, str]) -> CheckResult:
    if (summary := section.get(item)) is None:
        return
    yield Result(state=State.OK, summary=summary)


check_plugin_arbor_peakflow_tms_updates = CheckPlugin(
    name="arbor_peakflow_tms_updates",
    service_name="Config Update %s",
    discovery_function=inventory_peakflow_tms_updates,
    check_function=check_peakflow_tms_updates,
)
