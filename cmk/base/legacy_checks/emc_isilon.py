#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.emc.lib import DETECT_ISILON


def parse_emc_isilon(string_table: Sequence[StringTable]) -> Sequence[StringTable] | None:
    return string_table if any(string_table) else None


snmp_section_emc_isilon = SNMPSection(
    name="emc_isilon",
    detect=DETECT_ISILON,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12124.1.1",
            oids=["1", "2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12124.2.1",
            oids=["1", "2"],
        ),
    ],
    parse_function=parse_emc_isilon,
)


#   .--ClusterHealth------------------------------------------------------.


def discover_emc_isilon_clusterhealth(section: Sequence[StringTable]) -> DiscoveryResult:
    yield Service()


def check_emc_isilon_clusterhealth(section: Sequence[StringTable]) -> CheckResult:
    status = int(section[0][0][1])
    statusmap = ("ok", "attn", "down", "invalid")
    if status >= len(statusmap):
        yield Result(
            state=State.UNKNOWN, summary=f"ClusterHealth reports unidentified status {status}"
        )
        return

    state = State.OK if status == 0 else State.CRIT
    yield Result(state=state, summary=f"ClusterHealth reports status {statusmap[status]}")


check_plugin_emc_isilon_clusterhealth = CheckPlugin(
    name="emc_isilon_clusterhealth",
    service_name="Cluster Health",
    sections=["emc_isilon"],
    discovery_function=discover_emc_isilon_clusterhealth,
    check_function=check_emc_isilon_clusterhealth,
)

# .
#   .--NodeHealth------------------------------------------------------.


def discover_emc_isilon_nodehealth(section: Sequence[StringTable]) -> DiscoveryResult:
    yield Service()


def check_emc_isilon_nodehealth(section: Sequence[StringTable]) -> CheckResult:
    status = int(section[1][0][1])
    statusmap = ("ok", "attn", "down", "invalid")
    nodename = section[1][0][0]
    if status >= len(statusmap):
        yield Result(
            state=State.UNKNOWN, summary=f"nodeHealth reports unidentified status {status}"
        )
        return

    state = State.OK if status == 0 else State.CRIT
    yield Result(
        state=state, summary=f"nodeHealth for {nodename} reports status {statusmap[status]}"
    )


check_plugin_emc_isilon_nodehealth = CheckPlugin(
    name="emc_isilon_nodehealth",
    service_name="Node Health",
    sections=["emc_isilon"],
    discovery_function=discover_emc_isilon_nodehealth,
    check_function=check_emc_isilon_nodehealth,
)

# .
#   .--Nodes------------------------------------------------------.


def discover_emc_isilon_nodes(section: Sequence[StringTable]) -> DiscoveryResult:
    yield Service()


def check_emc_isilon_nodes(section: Sequence[StringTable]) -> CheckResult:
    _cluster_name, _cluster_health, configured_nodes, online_nodes = section[0][0]
    state = State.OK if configured_nodes == online_nodes else State.CRIT
    yield Result(
        state=state, summary=f"Configured Nodes: {configured_nodes} / Online Nodes: {online_nodes}"
    )


check_plugin_emc_isilon_nodes = CheckPlugin(
    name="emc_isilon_nodes",
    service_name="Nodes",
    sections=["emc_isilon"],
    discovery_function=discover_emc_isilon_nodes,
    check_function=check_emc_isilon_nodes,
)

# .
#   .--Cluster- and Node Name-------------------------------------------.


def discover_emc_isilon_names(section: Sequence[StringTable]) -> DiscoveryResult:
    yield Service()


def check_emc_isilon_names(section: Sequence[StringTable]) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Cluster Name is {section[0][0][0]}, Node Name is {section[1][0][0]}",
    )


check_plugin_emc_isilon_names = CheckPlugin(
    name="emc_isilon_names",
    service_name="Isilon Info",
    sections=["emc_isilon"],
    discovery_function=discover_emc_isilon_names,
    check_function=check_emc_isilon_names,
)

# .
