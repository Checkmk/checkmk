#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    exists,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Node:
    online: bool
    state: Literal["active", "passive"]
    forced: bool
    quality: float
    model: str
    version: str
    license: str
    priority: str
    serial: str


Section = Mapping[str, Node]


def parse_stormshield_cluster_node(string_table: StringTable) -> Section:
    return {
        index: Node(
            online=online == "1",
            state="active" if active == "2" else "passive",
            forced=statusforced == "1",
            quality=float(quality),
            model=model,
            version=version,
            license=license,
            priority=priority,
            serial=serial,
        )
        for (
            index,
            serial,
            online,
            model,
            version,
            license,
            quality,
            priority,
            statusforced,
            active,
            _uptime,
        ) in string_table
    }


def inventory_stormshield_cluster_node(section: Section) -> DiscoveryResult:
    yield from (Service(item=index) for index in section)


def check_stormshield_cluster_node(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (node := section.get(item)) is None:
        return

    if node.online:
        yield Result(state=State.OK, summary="Online")
    else:
        yield Result(state=State.CRIT, summary="Offline")

    if node.forced:
        yield Result(state=State.WARN, summary=f"HA-State: {node.state} (forced)")
    else:
        yield Result(state=State.OK, summary=f"HA-State: {node.state} (not forced)")

    yield from check_levels(
        node.quality, levels_lower=params["quality"], label="Quality", render_func=render.percent
    )

    yield Result(state=State.OK, summary=f"Model: {node.model}")
    yield Result(state=State.OK, summary=f"Version: {node.version}")
    yield Result(state=State.OK, summary=f"Role: {node.license}")
    yield Result(state=State.OK, summary=f"Priority: {node.priority}")
    yield Result(state=State.OK, summary=f"Serial: {node.serial}")


snmp_section_stormshield_cluster_node = SimpleSNMPSection(
    name="stormshield_cluster_node",
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.8"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        ),
        exists(".1.3.6.1.4.1.11256.1.11.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11.7.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    parse_function=parse_stormshield_cluster_node,
)

check_plugin_stormshield_cluster_node = CheckPlugin(
    name="stormshield_cluster_node",
    service_name="HA Member %s",
    discovery_function=inventory_stormshield_cluster_node,
    check_function=check_stormshield_cluster_node,
    check_ruleset_name="stormshield_quality",
    check_default_parameters={
        "quality": ("fixed", (80.0, 50.0)),
    },
)
