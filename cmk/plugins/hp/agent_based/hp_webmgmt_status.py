#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = Sequence[StringTable]

_STATUS_MAP: Mapping[str, tuple[State, str]] = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.UNKNOWN, "unused"),
    "3": (State.OK, "ok"),
    "4": (State.WARN, "warning"),
    "5": (State.CRIT, "critical"),
    "6": (State.CRIT, "non-recoverable"),
}


def parse_hp_webmgmt_status(string_table: Sequence[StringTable]) -> Section:
    return string_table


def discover_hp_webmgmt_status(section: Section) -> DiscoveryResult:
    yield from (Service(item=index) for index, _health in section[0])


def check_hp_webmgmt_status(item: str, section: Section) -> CheckResult:
    device_model = section[1][0][0] if section[1] and section[1][0] else ""
    serial_number = section[2][0][0] if section[2] and section[2][0] else ""
    for index, health in section[0]:
        if index != item:
            continue
        state, status_msg = _STATUS_MAP[health]
        summary = f"Device status: {status_msg}"
        if device_model and serial_number:
            summary += f" [Model: {device_model}, Serial Number: {serial_number}]"
        yield Result(state=state, summary=summary)
        return


snmp_section_hp_webmgmt_status = SNMPSection(
    name="hp_webmgmt_status",
    parse_function=parse_hp_webmgmt_status,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11"),
        exists(".1.3.6.1.4.1.11.2.36.1.1.5.1.1.*"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1",
            oids=["1", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1.9",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1.10",
            oids=["1"],
        ),
    ],
)


check_plugin_hp_webmgmt_status = CheckPlugin(
    name="hp_webmgmt_status",
    service_name="Status %s",
    discovery_function=discover_hp_webmgmt_status,
    check_function=check_hp_webmgmt_status,
)
