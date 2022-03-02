#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP-Cluster-Status SNMP Sections and Checks
"""

from typing import List, Mapping, Optional

from .agent_based_api.v1 import all_of, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.f5_bigip import (
    F5_BIGIP,
    F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
    F5BigipClusterStatusVSResult,
    VERSION_PRE_V11_2,
    VERSION_V11_2_PLUS,
)

NodeState = int

STATE_NAMES = {
    True: ("unknown", "offline", "forced offline", "standby", "active"),
    False: ("standby", "active 1", "active 2", "active"),
}


def parse_f5_bigip_cluster_status(
    string_table: List[StringTable],
) -> Optional[NodeState]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_cluster_status([[['4']]])
    4
    """
    return int(string_table[0][0][0]) if string_table[0] else None


def discover_f5_bigip_cluster_status(section: NodeState) -> DiscoveryResult:
    yield Service()


def _node_result(
    node_name: str,
    node_state: NodeState,
    is_gt_v11_2: bool,
    params: F5BigipClusterStatusVSResult,
) -> Result:
    """Turn given node details into
    >>> _node_result("", 4, True, {'type': 'active_standby'})
    Result(state=<State.OK: 0>, summary='Node is active')
    >>> _node_result("", 3, False, {'type': 'active_standby'})
    Result(state=<State.OK: 0>, summary='Node is active')
    """
    state_mapping_from_params = {int(k): v for k, v in params.get("v11_2_states", {}).items()}
    state_mapping = {**{0: 3, 1: 2, 2: 2, 3: 0, 4: 0}, **state_mapping_from_params}
    return Result(
        state=state(state_mapping[node_state] if is_gt_v11_2 else 0),
        summary="Node %sis %s"
        % (
            ("[%s] " % node_name) if node_name else "",
            STATE_NAMES[is_gt_v11_2][node_state],
        ),
    )


def _check_f5_bigip_cluster_status_common(
    params: F5BigipClusterStatusVSResult,
    section: NodeState,
    is_gt_v11_2: bool,
) -> CheckResult:
    yield _node_result("", section, is_gt_v11_2, params)


def _cluster_check_f5_bigip_cluster_status_common(
    params: F5BigipClusterStatusVSResult,
    section: Mapping[str, Optional[NodeState]],
    is_gt_v11_2: bool,
) -> CheckResult:
    """
    >>> for r in _cluster_check_f5_bigip_cluster_status_common(
    ...         params={'type': 'active_standby'},
    ...         section={'f5-bigip-5': 3, 'f5-bigip-6': 0},
    ...         is_gt_v11_2=True):
    ...     print(r)
    Result(state=<State.CRIT: 2>, summary='No active node found: ')
    Result(state=<State.OK: 0>, summary='Node [f5-bigip-5] is standby')
    Result(state=<State.UNKNOWN: 3>, summary='Node [f5-bigip-6] is unknown')
    """
    num_active_nodes = sum(x == STATE_NAMES[is_gt_v11_2].index("active") for x in section.values())

    if params["type"] == "active_standby" and num_active_nodes > 1:
        yield Result(state=state.CRIT, summary="More than 1 node is active: ")

    # Only applies if this check runs on a cluster
    elif num_active_nodes == 0 and len(section) > 1:
        yield Result(state=state.CRIT, summary="No active node found: ")

    for node_name, node_state in sorted(section.items()):
        if node_state is not None:
            yield _node_result(node_name, node_state, is_gt_v11_2, params)


# Older than v11.2


def check_f5_bigip_cluster_status(
    params: F5BigipClusterStatusVSResult, section: int
) -> CheckResult:
    """
    >>> for r in check_f5_bigip_cluster_status({"type": "active_standby"}, 3):
    ...     print(r)
    Result(state=<State.OK: 0>, summary='Node is active')
    """
    yield from _check_f5_bigip_cluster_status_common(params, section, False)


def cluster_check_f5_bigip_cluster_status(
    params: F5BigipClusterStatusVSResult,
    section: Mapping[str, Optional[NodeState]],
) -> CheckResult:
    """
    >>> for r in cluster_check_f5_bigip_cluster_status(
    ...         params={"type": "active_standby"},
    ...         section={"node1": 0, "node2": 3}):
    ...     print(r)
    Result(state=<State.OK: 0>, summary='Node [node1] is standby')
    Result(state=<State.OK: 0>, summary='Node [node2] is active')
    """
    yield from _cluster_check_f5_bigip_cluster_status_common(params, section, False)


register.snmp_section(
    name="f5_bigip_cluster_status",
    detect=all_of(F5_BIGIP, VERSION_PRE_V11_2),
    parse_function=parse_f5_bigip_cluster_status,
    fetch=[
        SNMPTree(base=".1.3.6.1.4.1.3375.2.1.1.1.1.19", oids=["0"]),  # sysAttrFailoverUnitMask
    ],
)

register.check_plugin(
    name="f5_bigip_cluster_status",  # name taken from pre-1.7 plugin
    service_name="BIG-IP Cluster Status",
    discovery_function=discover_f5_bigip_cluster_status,
    check_default_parameters=F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cluster_status",
    check_function=check_f5_bigip_cluster_status,
    cluster_check_function=cluster_check_f5_bigip_cluster_status,
)

# From v11.2 and up


def check_f5_bigip_cluster_status_v11_2(
    params: F5BigipClusterStatusVSResult, section: int
) -> CheckResult:
    yield from _check_f5_bigip_cluster_status_common(params, section, True)


def cluster_check_f5_bigip_cluster_status_v11_2(
    params: F5BigipClusterStatusVSResult,
    section: Mapping[str, Optional[NodeState]],
) -> CheckResult:
    yield from _cluster_check_f5_bigip_cluster_status_common(params, section, True)


register.snmp_section(
    name="f5_bigip_cluster_status_v11_2",
    detect=all_of(F5_BIGIP, VERSION_V11_2_PLUS),
    parse_function=parse_f5_bigip_cluster_status,
    fetch=[
        SNMPTree(base=".1.3.6.1.4.1.3375.2.1.14.3.1", oids=["0"]),  # sysCmFailoverStatusId
    ],
)

register.check_plugin(
    name="f5_bigip_cluster_status_v11_2",  # name taken from pre-1.7 plugin
    service_name="BIG-IP Cluster Status",
    discovery_function=discover_f5_bigip_cluster_status,
    check_default_parameters=F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cluster_status",
    check_function=check_f5_bigip_cluster_status_v11_2,
    cluster_check_function=cluster_check_f5_bigip_cluster_status_v11_2,
)

#
# F5-BIGIP-Cluster Config Sync - SNMP sections and Checks


def parse_f5_bigip_vcmpfailover(string_table: List[StringTable]) -> Optional[NodeState]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_vcmpfailover([[["0", "4"]]])
    4
    """
    # .1.3.6.1.4.1.3375.2.1.13.1.1.0 0 # sysVcmpNumber
    # .1.3.6.1.4.1.3375.2.1.14.1.1.0 3 # sysCmFailoverStatusId
    if not string_table[0]:
        return None
    count, status = string_table[0][0]
    if int(count) == 0:
        return NodeState(status)
    # do nothing if we're at a vCMP-/Host/
    return None


register.snmp_section(
    name="f5_bigip_vcmpfailover",
    detect=all_of(F5_BIGIP, VERSION_V11_2_PLUS),
    parse_function=parse_f5_bigip_vcmpfailover,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1",
            oids=[
                "13.1.1.0",  # sysVcmpNumber
                "14.3.1.0",  # sysCmFailoverStatusId
            ],
        ),
    ],
)

register.check_plugin(
    name="f5_bigip_vcmpfailover",  # name taken from pre-1.7 plugin
    service_name="BIG-IP vCMP Guest Failover Status",
    discovery_function=discover_f5_bigip_cluster_status,
    check_default_parameters=F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cluster_status",
    check_function=check_f5_bigip_cluster_status_v11_2,
    cluster_check_function=cluster_check_f5_bigip_cluster_status_v11_2,
)
