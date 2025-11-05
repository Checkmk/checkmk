#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.apc import DETECT


@dataclass
class Data:
    location: str
    state: tuple[str, int]


Section = Mapping[str, Data]
StringTable = list[list[str]]


def _get_state_text(state: int) -> str:
    state_text = {
        1: "Closed high mem",
        2: "Open low mem",
        3: "Disabled",
        4: "Not applicable",
    }
    return "{text} [{state}]".format(text=state_text.get(state, "unknown"), state=state)


def get_state_tuple_based_on_snmp_value(state: int, normal: int, severity: int) -> tuple[str, int]:
    severity_map = {
        #        | cmk State   | SNMP Severity  |
        #        |-------------|----------------|
        1: 0,  # | OK = 0      | Informational
        2: 1,  # | WARN = 1    | Warning
        3: 2,  # | CRIT = 2    | Severe
        4: 3,  # | UNKNOWN = 3 | Not applicable
    }

    current_state = _get_state_text(state)
    if normal == state:
        return (f"Normal state ({current_state})", 0)

    # State is not normal. Error with given severity
    severity_state = severity_map.get(severity, 3)
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


def check_apc_netbotz_drycontact(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    state_readable, state = data.state
    loc = data.location
    if loc:
        loc_info = "[%s] " % loc
    else:
        loc_info = ""
    yield state, f"{loc_info}{state_readable}"


def discover_apc_netbotz_drycontact(section):
    yield from ((item, {}) for item in section)


check_info["apc_netbotz_drycontact"] = LegacyCheckDefinition(
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
    service_name="DryContact %s",
    discovery_function=discover_apc_netbotz_drycontact,
    check_function=check_apc_netbotz_drycontact,
)
