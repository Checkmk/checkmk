#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, List, Literal, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import (
    any_of,
    contains,
    register,
    Result,
    Service,
    SNMPTree,
    State,
    type_defs,
)

_EA12x12_BASE = ".1.3.6.1.4.1.5040.1.2.4"
_EA12x6_BASE = ".1.3.6.1.4.1.5040.1.2.51"
_EA2x2_BASE = ".1.3.6.1.4.1.5040.1.2.52"

_OIDS_TO_FETCH = [
    "3.1.1.1.0",  # user defined description of the WebIO
    "1.3.1.1",  # the input port index
    "3.2.1.1.1",  # user defined description of every input
    "1.3.1.4",  # the state of the input
]

_DeviceStates = Literal["On", "Off"]


class Input(NamedTuple):
    state: _DeviceStates
    idx: str


Section = Mapping[str, Input]

STATE_TRANSLATION: Mapping[str, _DeviceStates] = {
    "0": "Off",
    "1": "On",
}

DEFAULT_STATE_EVALUATION = {
    "Off": int(State.CRIT),
    "On": int(State.OK),
}

STATE_EVAL_KEY = "evaluation_mode"
AS_DISCOVERED = "as_discovered"
STATES_DURING_DISC_KEY = "states_during_discovery"


def parse_wut_webio(string_table: List[type_defs.StringTable]) -> Optional[Section]:
    # We may have a EA12x6, EA2x2 or EA12x12
    webio_data = string_table[0] or string_table[1] or string_table[2]
    if not webio_data:
        return None

    return {
        f"{webio_data[0][0]} {port_name}": Input(
            state=STATE_TRANSLATION[state],
            idx=idx,
        )
        for _, idx, port_name, state in webio_data[1:]
    }


register.snmp_section(
    name="wut_webio",
    parse_function=parse_wut_webio,
    fetch=[
        SNMPTree(base=_EA12x6_BASE, oids=_OIDS_TO_FETCH),  # wtWebio577xxEA12x6
        SNMPTree(base=_EA2x2_BASE, oids=_OIDS_TO_FETCH),  # wtWebio577xxEA2x2
        SNMPTree(base=_EA12x12_BASE, oids=_OIDS_TO_FETCH),  # wtWebioEA12x12
    ],
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", _EA12x6_BASE),
        contains(".1.3.6.1.2.1.1.2.0", _EA2x2_BASE),
        contains(".1.3.6.1.2.1.1.2.0", _EA12x12_BASE),
    ),
)


def _get_state_evaluation_from_state(state: str) -> Mapping[str, int]:
    return {state_key: 0 if state == state_key else 2 for state_key in ("Off", "On")}


def discover_wut_webio(section: Section) -> type_defs.DiscoveryResult:

    yield from [
        Service(item=item, parameters={STATES_DURING_DISC_KEY: input_.state})
        for item, input_ in section.items()
    ]


def check_wut_webio(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    if item not in section:
        return

    data = section[item]
    current_state = data.state
    if params[STATE_EVAL_KEY] == AS_DISCOVERED:
        state_map = _get_state_evaluation_from_state(params[STATES_DURING_DISC_KEY])
    else:
        state_map = params[STATE_EVAL_KEY]

    yield Result(
        state=State(state_map[current_state]),
        summary=f"Input (Index: {data.idx}) is in state: {data.state}",
    )


register.check_plugin(
    name="wut_webio",
    service_name="W&T %s",
    discovery_function=discover_wut_webio,
    check_function=check_wut_webio,
    check_default_parameters={
        STATE_EVAL_KEY: DEFAULT_STATE_EVALUATION,
    },
    check_ruleset_name="wut_webio",
)
