#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    not_equals,
    OIDEnd,
    register,
    render,
    Service,
    SNMPTree,
    startswith,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

OID_SysObjectID = ".1.3.6.1.2.1.1.2.0"

Section = Dict


def parse_fortigate_node_memory(string_table: List[StringTable]) -> Section:
    if len(string_table[0]) == 1:
        return {"Cluster": float(string_table[0][0][1])}

    return {(h if h else f"Node {i}"): float(m) for h, m, i in string_table[0]}


register.snmp_section(
    name="fortigate_node_memory",
    detect=all_of(
        startswith(OID_SysObjectID, ".1.3.6.1.4.1.12356.101.1"),
        # exclude FortiGates in standalone mode:
        not_equals(".1.3.6.1.4.1.12356.101.13.1.1.0", "1"),
    ),
    parse_function=parse_fortigate_node_memory,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.2.1.1",
            oids=[
                "11",
                "4",
                OIDEnd(),
            ],
        ),
    ],
)


def discovery_fortigate_node_memory(section: Section) -> DiscoveryResult:
    for k in section.keys():
        yield Service(item=k)


def check_fortigate_node_memory(item, params: Mapping[str, Any], section: Section) -> CheckResult:
    memory = section.get(item)
    if memory is None:
        return

    yield from check_levels(
        memory,
        metric_name="mem_used_percent",
        levels_upper=params["levels"],
        boundaries=(0.0, 100.0),
        render_func=render.percent,
        label="Usage",
    )


register.check_plugin(
    name="fortigate_node_memory",
    service_name="Memory %s",
    discovery_function=discovery_fortigate_node_memory,
    check_function=check_fortigate_node_memory,
    check_ruleset_name="fortigate_node_memory",
    check_default_parameters={"levels": (70.0, 80.0)},
)
