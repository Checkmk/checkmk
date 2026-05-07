#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP Walk
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.1.6 Leckagekontrolle-RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.5 Pumpe 1 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.6 Pumpe 2 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.1.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.5 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.1.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.5 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.6 2


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.apc.lib_ats import DETECT


@dataclass
class Data:
    location: str
    state: tuple[str, State]


Section = Mapping[str, Data]


def _get_state_text(state: int) -> str:
    state_text = {
        1: "Closed high mem",
        2: "Open low mem",
        3: "Disabled",
        4: "Not applicable",
    }
    return "{text} [{state}]".format(text=state_text.get(state, "unknown"), state=state)


def get_state_tuple_based_on_snmp_value(
    state: int, normal: int, severity: int
) -> tuple[str, State]:
    severity_map = {
        1: State.OK,  # Informational
        2: State.WARN,  # Warning
        3: State.CRIT,  # Severe
        4: State.UNKNOWN,  # Not applicable
    }

    current_state = _get_state_text(state)
    if normal == state:
        return (f"Normal state ({current_state})", State.OK)

    # State is not normal. Error with given severity
    severity_state = severity_map.get(severity, State.UNKNOWN)
    return (
        f"State: {current_state} but expected {_get_state_text(normal)}",
        severity_state,
    )


def parse_apc_netbotz_drycontact(string_table: StringTable) -> Section:
    parsed = {}

    for idx, inst, loc, state, normal, severity in string_table:
        parsed[f"{inst} {idx}"] = Data(
            location=loc,
            state=get_state_tuple_based_on_snmp_value(
                int(state),
                int(normal),
                int(severity),
            ),
        )

    return parsed


def check_apc_netbotz_drycontact(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    state_readable, state = data.state
    loc = data.location
    if loc:
        loc_info = "[%s] " % loc
    else:
        loc_info = ""
    yield Result(state=state, summary=f"{loc_info}{state_readable}")


def discover_apc_netbotz_drycontact(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_apc_netbotz_drycontact = SimpleSNMPSection(
    name="apc_netbotz_drycontact",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.3",
        oids=[
            OIDEnd(),  # Index
            # memInputsStatusEntry
            "2.1.3",  # memInputsStatusInputName
            "2.1.4",  # memInputsStatusInputLocation
            "2.1.5",  # memInputsStatusCurrentState
            # memInputsConfigEntry
            "4.1.7",  # memInputNormalState
            "4.1.8",  # memInputAbnormalSeverity
        ],
    ),
    parse_function=parse_apc_netbotz_drycontact,
)

check_plugin_apc_netbotz_drycontact = CheckPlugin(
    name="apc_netbotz_drycontact",
    service_name="DryContact %s",
    discovery_function=discover_apc_netbotz_drycontact,
    check_function=check_apc_netbotz_drycontact,
)
