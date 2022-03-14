#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Mapping, NamedTuple

from .agent_based_api.v1 import (
    all_of,
    any_of,
    check_levels,
    equals,
    exists,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

_SERVICE_STATE_MAP = {"0": "down", "1": "up"}


class StormshieldService(NamedTuple):
    state: str
    uptime: int


Section = Mapping[str, StormshieldService]


def parse_stormshield_services(string_table: List[List[str]]) -> Section:
    section = {}
    for name, state, r_uptime in string_table:
        try:
            section[name] = StormshieldService(state, int(r_uptime))
        except ValueError:
            section[name] = StormshieldService("down", 0)

    return section


register.snmp_section(
    name="stormshield_services",
    parse_function=parse_stormshield_services,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.7.1.1",
        oids=[
            "2",  # snsServicesName
            "3",  # snsServicesState
            "4",  # snsServicesUptime
        ],
    ),
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        ),
        exists(".1.3.6.1.4.1.11256.1.0.1.0"),
    ),
)


def discover_stormshield_services(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name, service in section.items() if service.state == "1")


def check_stormshield_services(item: str, section: Section) -> CheckResult:
    service = section.get(item)
    if service is None:
        return

    state_label = _SERVICE_STATE_MAP[service.state]
    yield Result(state=State(state_label == "down"), summary=state_label.title())

    if state_label == "down":
        return

    yield from check_levels(
        service.uptime,
        metric_name="uptime",
        render_func=render.timespan,
        label="Uptime",
    )


register.check_plugin(
    name="stormshield_services",
    service_name="Service %s",
    discovery_function=discover_stormshield_services,
    check_function=check_stormshield_services,
)
