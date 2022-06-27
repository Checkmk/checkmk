#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Tuple

from .agent_based_api.v1 import equals, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.sentry import DEVICE_STATES_V4

Section = Mapping[str, int]

OUTLET_STATES: Mapping[int, Tuple[State, str]] = {
    0: (State.OK, "off"),
    1: (State.OK, "on"),
    2: (State.WARN, "off wait"),
    3: (State.WARN, "on wait"),
    4: (State.CRIT, "off error"),
    5: (State.CRIT, "on error"),
    6: (State.CRIT, "no comm"),
    7: (State.CRIT, "reading"),
    8: (State.CRIT, "off fuse"),
    9: (State.CRIT, "on fuse"),
}


def parse_sentry_pdu_outlets(string_table: StringTable) -> Section:
    parsed = {}
    for outlet_id, outlet_name, outlet_state_str in string_table:
        outlet_name = outlet_name.replace("Outlet", "")
        outlet_id_name = "%s %s" % (outlet_id, outlet_name)
        parsed[outlet_id_name] = int(outlet_state_str)
    return parsed


register.snmp_section(
    name="sentry_pdu_outlets",
    parse_function=parse_sentry_pdu_outlets,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.2.3.1",
        oids=[
            "2",
            "3",
            "5",
        ],
    ),
)

register.snmp_section(
    name="sentry_pdu_outlets_v4",
    parse_function=parse_sentry_pdu_outlets,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.4.1.8",
        oids=[
            "2.1.2",
            "2.1.3",
            "3.1.2",
        ],
    ),
)


def discovery_sentry_pdu_outlets(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_outlets(
    item: str, section: Section, outlet_states: Mapping[int, Tuple[State, str]]
) -> CheckResult:
    outlet_state = section.get(item)
    if outlet_state is None:
        return

    if outlet_state in outlet_states:
        state, status = outlet_states[outlet_state]
        yield Result(state=state, summary=f"Status: {status}")
    else:
        yield Result(state=State.UNKNOWN, summary=f"Unhandled state: {outlet_state}")


def check_sentry_pdu_outlets(item: str, section: Section) -> CheckResult:
    yield from check_outlets(item, section, OUTLET_STATES)


register.check_plugin(
    name="sentry_pdu_outlets",
    service_name="Outlet %s",
    discovery_function=discovery_sentry_pdu_outlets,
    check_function=check_sentry_pdu_outlets,
)


def check_sentry_pdu_outlets_v4(item: str, section: Section) -> CheckResult:
    yield from check_outlets(item, section, DEVICE_STATES_V4)


register.check_plugin(
    name="sentry_pdu_outlets_v4",
    service_name="Outlet %s",
    discovery_function=discovery_sentry_pdu_outlets,
    check_function=check_sentry_pdu_outlets_v4,
)
