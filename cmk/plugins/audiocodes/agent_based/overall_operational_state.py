#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

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

from .lib import (
    DETECT_AUDIOCODES,
    OPERATIONAL_STATE_MAPPING,
    OPState,
)


@dataclass(frozen=True, kw_only=True)
class GWSeverity:
    name: str
    state: State


GW_SEVERITY_MAPPING = {
    "0": GWSeverity(name="No alarm", state=State.OK),
    "1": GWSeverity(name="Indeterminate", state=State.UNKNOWN),
    "2": GWSeverity(name="Warning", state=State.WARN),
    "3": GWSeverity(name="Minor", state=State.WARN),
    "4": GWSeverity(name="Major", state=State.CRIT),
    "5": GWSeverity(name="Critical", state=State.CRIT),
}


@dataclass(frozen=True, kw_only=True)
class OperationalState:
    op_state: OPState
    gw_severity: GWSeverity
    error_message: str
    error_id: str


def parse_audiocodes_overall_operational_state(
    string_table: StringTable,
) -> OperationalState | None:
    if not string_table:
        return None

    op_state, gw_severity, error_message, error_id = string_table[0]
    return OperationalState(
        op_state=OPERATIONAL_STATE_MAPPING[op_state],
        gw_severity=GW_SEVERITY_MAPPING[gw_severity],
        error_message=error_message,
        error_id=error_id,
    )


snmp_section_audiocodes_overall_operational_state = SimpleSNMPSection(
    name="audiocodes_overall_operational_state",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.2.5",
        oids=[
            "2.0",  # acSysStateOperational
            "4.0",  # acSysStateGWSeverity
            "6.0",  # acSysStateErrorMessage
            "7.0",  # acSysStateErrorID
        ],
    ),
    parse_function=parse_audiocodes_overall_operational_state,
)


def discover_audiocodes_overall_operational_state(
    section: OperationalState,
) -> DiscoveryResult:
    yield Service()


def check_audiocodes_overall_operational_state(
    section: OperationalState,
) -> CheckResult:
    yield Result(
        state=section.gw_severity.state,
        summary=f"Gateway: {section.gw_severity.name}",
    )
    yield Result(
        state=section.op_state.state,
        notice=f"Highest alarm severity: {section.op_state.name}",
        details=(
            f"Error message: {section.error_message or '(empty)'}\nError ID: {section.error_id or '(empty)'}"
        )
        if section.error_message or section.error_id
        else None,
    )


check_plugin_audiocodes_overall_operational_state = CheckPlugin(
    name="audiocodes_overall_operational_state",
    service_name="Operational state",
    discovery_function=discover_audiocodes_overall_operational_state,
    check_function=check_audiocodes_overall_operational_state,
)
