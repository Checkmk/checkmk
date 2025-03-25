#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    not_equals,
    OIDEnd,
    render,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)

OID_SysObjectID = ".1.3.6.1.2.1.1.2.0"

Section = dict


def parse_fortigate_node_memory(string_table: Sequence[StringTable]) -> Section:
    if len(string_table[0]) == 1:
        return {"Cluster": float(string_table[0][0][1])}

    return {(h if h else f"Node {i}"): float(m) for h, m, i in string_table[0]}


snmp_section_fortigate_node_memory = SNMPSection(
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


def check_fortigate_node_memory(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    memory = section.get(item)
    if memory is None:
        return

    yield from check_levels_v1(
        memory,
        metric_name="mem_used_percent",
        levels_upper=params["levels"],
        boundaries=(0.0, 100.0),
        render_func=render.percent,
        label="Usage",
    )


check_plugin_fortigate_node_memory = CheckPlugin(
    name="fortigate_node_memory",
    service_name="Memory %s",
    discovery_function=discovery_fortigate_node_memory,
    check_function=check_fortigate_node_memory,
    check_ruleset_name="fortigate_node_memory",
    check_default_parameters={"levels": (70.0, 80.0)},
)
