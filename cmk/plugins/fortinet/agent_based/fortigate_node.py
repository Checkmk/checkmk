#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    not_equals,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

#
# monitoring of cluster members (nodes) in fortigate high availability tree
#

# cluster info
# .1.3.6.1.4.1.12356.101.13.1.1.0 3
# .1.3.6.1.4.1.12356.101.13.1.7.0 DEPTHA-HA

# node info
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.1 NODE-01
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.2 NODE-02
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.1 13
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.2 1
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.1 52
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.2 21
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.1 1884
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.2 742

# only one node given => standalone cluster
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.1  ""
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.1  0
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.1  19
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.1  443

#   .--Info----------------------------------------------------------------.
#   |                         ___        __                                |
#   |                        |_ _|_ __  / _| ___                           |
#   |                         | || '_ \| |_ / _ \                          |
#   |                         | || | | |  _| (_) |                         |
#   |                        |___|_| |_|_|  \___/                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class ClusterInfo:
    system_mode: str
    group_name: str


@dataclass(frozen=True)
class Node:
    cpu: float
    memory: int
    sessions: int


@dataclass(frozen=True)
class Section:
    cluster_info: ClusterInfo | None
    nodes: Mapping[str, Node]


def parse_fortigate_node(string_table: Sequence[StringTable]) -> Section:
    nodes: dict[str, Node] = {}
    for hostname, cpu_str, memory_str, sessions_str, oid_end in string_table[1]:
        # This means we have a standalone cluster
        if len(string_table[1]) == 1:
            item_name = "Cluster"
        elif hostname:
            item_name = hostname
        else:
            item_name = f"Node {oid_end}"

        nodes.setdefault(
            item_name,
            Node(
                cpu=float(cpu_str),
                memory=int(memory_str),
                sessions=int(sessions_str),
            ),
        )

    cluster_info = None
    if string_table[0]:
        system_mode, group_name = string_table[0][0]
        cluster_info = ClusterInfo(system_mode=system_mode, group_name=group_name)

    return Section(cluster_info=cluster_info, nodes=nodes)


def discover_fortigate_cluster(section: Section) -> DiscoveryResult:
    if section.cluster_info is not None:
        yield Service()


def check_fortigate_cluster(section: Section) -> CheckResult:
    map_mode = {
        "1": "Standalone",
        "2": "Active/Active",
        "3": "Active/Passive",
    }

    if (cluster_info := section.cluster_info) is not None:
        yield Result(
            state=State.OK,
            summary=(
                f"System mode: {map_mode[cluster_info.system_mode]}, "
                f"Group: {cluster_info.group_name}"
            ),
        )


snmp_section_fortigate_node = SNMPSection(
    name="fortigate_node",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        not_equals(".1.3.6.1.4.1.12356.101.13.1.1.0", "1"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.1",
            oids=["1", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.2.1.1",
            oids=["11", "3", "4", "6", OIDEnd()],
        ),
    ],
    parse_function=parse_fortigate_node,
)


check_plugin_fortigate_node = CheckPlugin(
    name="fortigate_node",
    service_name="Cluster Info",
    discovery_function=discover_fortigate_cluster,
    check_function=check_fortigate_cluster,
)

# .
#   .--CPU-----------------------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_fortigate_node_cpu(section: Section) -> DiscoveryResult:
    for hostname in section.nodes:
        yield Service(item=hostname)


def check_fortigate_node_cpu(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (node := section.nodes.get(item)) is None:
        return

    yield from check_cpu_util(
        util=node.cpu,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_fortigate_node_cpu = CheckPlugin(
    name="fortigate_node_cpu",
    service_name="CPU utilization %s",
    sections=["fortigate_node"],
    discovery_function=discover_fortigate_node_cpu,
    check_function=check_fortigate_node_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)

# .
#   .--Sessions------------------------------------------------------------.
#   |                ____                _                                 |
#   |               / ___|  ___  ___ ___(_) ___  _ __  ___                 |
#   |               \___ \ / _ \/ __/ __| |/ _ \| '_ \/ __|                |
#   |                ___) |  __/\__ \__ \ | (_) | | | \__ \                |
#   |               |____/ \___||___/___/_|\___/|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_fortigate_node_ses(section: Section) -> DiscoveryResult:
    for hostname in section.nodes:
        yield Service(item=hostname)


def check_fortigate_node_ses(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (node := section.nodes.get(item)) is None:
        return

    yield from check_levels_v1(
        node.sessions,
        metric_name="session",
        levels_upper=params["levels"],
        render_func=str,
        label="Sessions",
    )


check_plugin_fortigate_node_sessions = CheckPlugin(
    name="fortigate_node_sessions",
    service_name="Sessions %s",
    sections=["fortigate_node"],
    discovery_function=discover_fortigate_node_ses,
    check_function=check_fortigate_node_ses,
    check_ruleset_name="fortigate_node_sessions",
    check_default_parameters={"levels": (100000, 150000)},
)
