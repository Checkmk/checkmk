#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm_svc.lib import parse_ibm_svc_with_header


@dataclass(frozen=True)
class Node:
    name: str
    status: str


# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# check is SNMP-Based, then remove this section

# newer agent output with more columns
# 1:N1_164191:10001AA202:500507680100D7CA:online:0:io_grp0:no:2040000051442002:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n1164191::164191:::::
# 2:N2_164373:10001AA259:500507680100D874:online:0:io_grp0:no:2040000051442149:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n2164373::164373:::::
# 5:N3_162711:100025E317:500507680100D0A7:online:1:io_grp1:no:2040000085543047:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n3162711::162711:::::
# 6:N4_164312:100025E315:500507680100D880:online:1:io_grp1:yes:2040000085543045:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n4164312::164312:::::


Section = Mapping[str, Sequence[Node]]


def parse_ibm_svc_node(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "name",
        "UPS_serial_number",
        "WWNN",
        "status",
        "IO_group_id",
        "IO_group_name",
        "config_node",
        "UPS_unique_id",
        "hardware",
        "iscsi_name",
        "iscsi_alias",
        "panel_name",
        "enclosure_id",
        "canister_id",
        "enclosure_serial_number",
        "site_id",
        "site_name",
    ]
    parsed: dict[str, list[Node]] = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        for data in rows:
            parsed.setdefault(data["IO_group_name"], []).append(
                Node(name=data["name"], status=data["status"])
            )
    return parsed


def discover_ibm_svc_node(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ibm_svc_node(item: str, section: Section) -> CheckResult:
    if not (nodes := section.get(item)):
        return
    messages = []
    online_nodes = 0
    nodes_of_iogroup = 0

    for node in nodes:
        messages.append(f"Node {node.name} is {node.status}")
        nodes_of_iogroup += 1
        if node.status == "online":
            online_nodes += 1

    if nodes_of_iogroup == 0:
        yield Result(state=State.UNKNOWN, summary=f"IO Group {item} not found in agent output")
        return

    if nodes_of_iogroup == online_nodes:
        state = State.OK
    elif online_nodes == 0:
        state = State.CRIT
    else:
        state = State.WARN

    # sorted is needed for deterministic test results
    yield Result(state=state, summary=", ".join(sorted(messages)))


agent_section_ibm_svc_node = AgentSection(
    name="ibm_svc_node",
    parse_function=parse_ibm_svc_node,
)


check_plugin_ibm_svc_node = CheckPlugin(
    name="ibm_svc_node",
    service_name="IO Group %s",
    discovery_function=discover_ibm_svc_node,
    check_function=check_ibm_svc_node,
)
