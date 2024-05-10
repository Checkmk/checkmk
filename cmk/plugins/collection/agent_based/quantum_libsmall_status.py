#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

DEVICE_TYPE_MAP = {
    "1": "Power",
    "2": "Cooling",
    "3": "Control",
    "4": "Connectivity",
    "5": "Robotics",
    "6": "Media",
    "7": "Drive",
    "8": "Operator action request",
}

RAS_STATUS_MAP = {
    "1": (State.OK, "good"),
    "2": (State.CRIT, "failed"),
    "3": (State.CRIT, "degraded"),
    "4": (State.WARN, "warning"),
    "5": (State.OK, "informational"),
    "6": (State.UNKNOWN, "unknown"),
    "7": (State.UNKNOWN, "invalid"),
}

OPNEED_STATUS_MAP = {
    "0": (State.OK, "no"),
    "1": (State.CRIT, "yes"),
    "2": (State.OK, "no"),
}

_Section = Sequence[tuple[str, str]]


def parse_quantum_libsmall_status(string_table: Sequence[StringTable]) -> _Section:
    parsed = []
    for line in string_table:
        for oidend, dev_state in line:
            dev_type = DEVICE_TYPE_MAP.get(oidend.split(".")[0])
            if dev_type is None or not dev_state:
                continue
            parsed.append((dev_type, dev_state))
    return parsed


def discovery_quantum_libsmall_status(section: _Section) -> DiscoveryResult:
    if section:
        yield Service(item=None)


def check_quantum_libsmall_status(section: _Section) -> CheckResult:
    for dev_type, dev_state in section:
        if dev_type == "Operator action request":
            state, state_readable = OPNEED_STATUS_MAP.get(
                dev_state, (State.UNKNOWN, "unknown[%s]" % dev_state)
            )
        else:
            state, state_readable = RAS_STATUS_MAP.get(
                dev_state, (State.UNKNOWN, "unknown[%s]" % dev_state)
            )
        yield Result(state=state, summary=f"{dev_type}: {state_readable}")


snmp_section_quantum_libsmall_status = SNMPSection(
    name="quantum_libsmall_status",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        contains(".1.3.6.1.4.1.3697.1.10.10.1.10.0", "Quantum Small Library Product"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3697.1.10.10.1.15",
            oids=[OIDEnd(), "10"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3764.1.10.10",
            oids=[OIDEnd(), "12"],
        ),
    ],
    parse_function=parse_quantum_libsmall_status,
)


check_plugin_quantum_libsmall_status = CheckPlugin(
    name="quantum_libsmall_status",
    service_name="Tape library status",
    discovery_function=discovery_quantum_libsmall_status,
    check_function=check_quantum_libsmall_status,
)
