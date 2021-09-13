#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping

from .agent_based_api.v1 import equals, Metric, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, Mapping[str, str]]

_KEYS = [
    "type",
    "admin_status",
    "oper_status",
    "output",
    "input",
]


def parse_adva_fsp_if(string_table: List[StringTable]) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_adva_fsp_if([[
    ... ['269091841', 'CH-1-4-C1', '1', '1', '1', '-31', '-27'],
    ... ['269091842', '', '1', '2', '2', '-65535', '-65535'],
    ... ]]))
    {'269091842': {'admin_status': '2',
                   'input': '-65535',
                   'oper_status': '2',
                   'output': '-65535',
                   'type': '1'},
     'CH-1-4-C1': {'admin_status': '1',
                   'input': '-27',
                   'oper_status': '1',
                   'output': '-31',
                   'type': '1'}}
    """
    return {line[1] or line[0]: dict(zip(_KEYS, line[2:])) for line in string_table[0]}


register.snmp_section(
    name="adva_fsp_if",
    parse_function=parse_adva_fsp_if,
    fetch=[
        SNMPTree(
            base=".1.3.6.1",
            oids=[
                "2.1.2.2.1.1",  # ifIndex
                "2.1.2.2.1.2",  # ifDescr
                "2.1.2.2.1.3",  # ifType
                "2.1.2.2.1.7",  # ifAdminStatus
                "2.1.2.2.1.8",  # ifOperStatus
                "4.1.2544.1.11.2.4.3.5.1.4",  # opticalIfDiagOutputPower
                "4.1.2544.1.11.2.4.3.5.1.3",  # opticalIfDiagInputPower
            ],
        ),
    ],
    detect=equals(".1.3.6.1.2.1.1.1.0", "Fiber Service Platform F7"),
    supersedes=["if", "if64"],
)

_MONITORED_TYPES = ["1", "6", "56"]
_MONITORED_ADMIN_STATES = ["1"]


def discover_adva_fsp_if(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, interface in section.items()
        if interface["type"] in _MONITORED_TYPES
        and interface["admin_status"] in _MONITORED_ADMIN_STATES
    )


_MAP_OPER_STATUS = {
    "1": ("up", State.OK),
    "2": ("down", State.CRIT),
    "3": ("testing", State.WARN),
    "4": ("unknown", State.UNKNOWN),
    "5": ("dormant", State.WARN),
    "6": ("notPresent", State.CRIT),
    "7": ("lowerLayerDown", State.CRIT),
}

_MAP_ADMIN_STATUS = {
    "1": ("up", State.OK),
    "2": ("down", State.CRIT),
    "3": ("testing", State.WARN),
}


def check_adva_fsp_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    interface = section.get(item)
    if not interface:
        return

    admintxt, adminstate = _MAP_OPER_STATUS[interface["admin_status"]]
    opertxt, operstate = _MAP_OPER_STATUS[interface["oper_status"]]
    yield Result(
        state=State.worst(adminstate, operstate),
        summary="Admin/Operational State: %s/%s" % (admintxt, opertxt),
    )

    for power_type in ["output", "input"]:
        try:
            power = float(interface[power_type]) / 10
        except ValueError:
            if not item.startswith("S"):  # if no service interface and no power parameter
                yield Result(
                    state=State.WARN,
                    summary="%s power: n.a." % power_type.title(),
                )
            continue

        params_key = "limits_%s_power" % power_type
        if params_key in params:
            lower, upper = params[params_key]
            mon_state = State.OK if lower <= power <= upper else State.CRIT
        else:
            mon_state = State.OK
            upper = None

        yield Result(
            state=mon_state,
            summary="%s power: %.1f dBm" % (power_type.title(), power),
        )
        yield Metric(
            "%s_power" % power_type,
            power,
            levels=(None, upper),
            boundaries=(0, None),
        )


register.check_plugin(
    name="adva_fsp_if",
    service_name="Interface %s",
    discovery_function=discover_adva_fsp_if,
    check_ruleset_name="adva_ifs",
    check_default_parameters={},
    check_function=check_adva_fsp_if,
)
