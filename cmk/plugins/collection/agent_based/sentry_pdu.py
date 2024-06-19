#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.sentry import DEVICE_STATES_V4


class PDU(NamedTuple):
    state: int
    power: int | None


Section = Mapping[str, PDU]

_STATES_INT_TO_READABLE: Mapping[int, str] = {
    0: "off",
    1: "on",
    2: "off wait",
    3: "on wait",
    4: "off error",
    5: "on error",
    6: "no comm",
}

_STATE_TO_MONSTATE: Mapping[str, State] = {
    "unknown": State.UNKNOWN,
}


def parse_sentry_pdu(string_table: StringTable) -> Section:
    """
    >>> parse_sentry_pdu([["TowerA_InfeedA", "1", "1097"], ["TowerA_InfeedB", "21", "0"], ["TowerA_InfeedC", "1", ""]])
    {'TowerA_InfeedA': PDU(state=1, power=1097), 'TowerA_InfeedB': PDU(state=21, power=0), 'TowerA_InfeedC': PDU(state=1, power=None)}
    """
    return {
        name: PDU(
            int(state),
            int(power_str) if power_str else None,
        )
        for name, state, power_str in string_table
    }


snmp_section_sentry_pdu = SimpleSNMPSection(
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

snmp_section_sentry_pdu_v4 = SimpleSNMPSection(
    name="sentry_pdu_v4",
    parse_function=parse_sentry_pdu,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.4.1.3",
        oids=[
            "2.1.3",
            "3.1.2",
            "3.1.3",
        ],
    ),
)


def discovery_sentry_pdu(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_sentry_pdu(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (pdu := section.get(item)):
        return

    readable_state = _STATES_INT_TO_READABLE.get(pdu.state, "unknown")

    if "required_state" in params and readable_state != params["required_state"]:
        yield Result(state=State.CRIT, summary=f"Status: {readable_state}")
    else:
        yield Result(
            state=_STATE_TO_MONSTATE.get(readable_state, State.OK),
            summary=f"Status: {readable_state}",
        )

    if pdu.power:
        yield Result(state=State.OK, summary=f"Power: {pdu.power} Watt")
        yield Metric(name="power", value=pdu.power)


check_plugin_sentry_pdu = CheckPlugin(
    name="sentry_pdu",
    service_name="Plug %s",
    discovery_function=discovery_sentry_pdu,
    check_function=check_sentry_pdu,
    check_ruleset_name="plugs",
    check_default_parameters={},
)


def check_sentry_pdu_v4(item: str, section: Section) -> CheckResult:
    if not (pdu := section.get(item)):
        return

    if pdu.state in DEVICE_STATES_V4:
        state, status = DEVICE_STATES_V4[pdu.state]
        yield Result(state=state, summary=f"Status: {status}")
    else:
        yield Result(state=State.UNKNOWN, summary=f"Status: {pdu.state}")

    if pdu.power:
        yield Result(state=State.OK, summary=f"Power: {pdu.power} Watt")
        yield Metric(name="power", value=pdu.power)


check_plugin_sentry_pdu_v4 = CheckPlugin(
    name="sentry_pdu_v4",
    service_name="Plug %s",
    discovery_function=discovery_sentry_pdu,
    check_function=check_sentry_pdu_v4,
)
