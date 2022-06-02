#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import equals, Metric, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class PDU(NamedTuple):
    state: str
    power: Optional[int]


Section = Mapping[str, PDU]

_STATES_INT_TO_READABLE: Mapping[str, str] = {
    "0": "off",
    "1": "on",
    "2": "off wait",
    "3": "on wait",
    "4": "off error",
    "5": "on error",
    "6": "no comm",
}

_STATE_TO_MONSTATE: Mapping[str, State] = {
    "unknown": State.UNKNOWN,
}


def parse_sentry_pdu(string_table: StringTable) -> Section:
    """
    >>> parse_sentry_pdu([["TowerA_InfeedA", "1", "1097"], ["TowerA_InfeedB", "21", "0"], ["TowerA_InfeedC", "1", ""]])
    {'TowerA_InfeedA': PDU(state='on', power=1097), 'TowerA_InfeedB': PDU(state='unknown', power=0), 'TowerA_InfeedC': PDU(state='on', power=None)}
    """
    return {
        name: PDU(
            _STATES_INT_TO_READABLE.get(
                state,
                "unknown",
            ),
            int(power_str) if power_str else None,
        )
        for name, state, power_str in string_table
    }


register.snmp_section(
    name="sentry_pdu",
    parse_function=parse_sentry_pdu,
    detect=equals(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.1718.3",
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.2.2.1",
        oids=[
            "3",
            "5",
            "12",
        ],
    ),
)


def discovery_sentry_pdu(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name, pdu in section.items())


def check_sentry_pdu(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (pdu := section.get(item)):
        return

    if "required_state" in params and pdu.state != params["required_state"]:
        yield Result(state=State.CRIT, summary=f"Status: {pdu.state}")
    else:
        yield Result(
            state=_STATE_TO_MONSTATE.get(pdu.state, State.OK),
            summary=f"Status: {pdu.state}",
        )

    if pdu.power:
        yield Result(state=State.OK, summary=f"Power: {pdu.power} Watt")
        yield Metric(name="power", value=pdu.power)


register.check_plugin(
    name="sentry_pdu",
    service_name="Plug %s",
    discovery_function=discovery_sentry_pdu,
    check_function=check_sentry_pdu,
    check_ruleset_name="plugs",
    check_default_parameters={},
)
