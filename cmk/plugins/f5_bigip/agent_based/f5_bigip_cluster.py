#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""F5-BIGIP-Cluster Config Sync - SNMP sections and Checks"""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    all_of,
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
from cmk.plugins.f5_bigip.lib import F5_BIGIP, VERSION_PRE_V11, VERSION_V11_PLUS


class NodeState(NamedTuple):
    state: str
    description: str


# Config sync status as reported by the device, mapped to the parameter key it is
# configured under and the name it is reported by.
CONFIG_SYNC_STATES: Mapping[str, tuple[str, str]] = {
    "0": ("unknown", "Unknown"),
    "1": ("syncing", "Syncing"),
    "2": ("need_manual_sync", "Need Manual Sync"),
    "3": ("in_sync", "In Sync"),
    "4": ("sync_failed", "Sync Failed"),
    "5": ("sync_disconnected", "Sync Disconnected"),
    "6": ("standalone", "Standalone"),
    "7": ("awaiting_initial_sync", "Awaiting Initial Sync"),
    "8": ("incompatible_version", "Incompatible Version"),
    "9": ("partial_sync", "Partial Sync"),
}

CONFIG_SYNC_DEFAULT_PARAMETERS: Mapping[str, int] = {
    "unknown": State.UNKNOWN.value,
    "syncing": State.OK.value,
    "need_manual_sync": State.WARN.value,
    "in_sync": State.OK.value,
    "sync_failed": State.CRIT.value,
    "sync_disconnected": State.CRIT.value,
    "standalone": State.CRIT.value,
    "awaiting_initial_sync": State.WARN.value,
    "incompatible_version": State.CRIT.value,
    "partial_sync": State.CRIT.value,
}


def discover_f5_bigip_config_sync(section: NodeState) -> DiscoveryResult:
    # run inventory unless we found a device in unconfigured state
    # don't need to loop over the input as there's only one status
    if section.state != "-1":
        yield Service()


def parse_f5_bigip_config_sync_pre_v11(string_table: Sequence[StringTable]) -> NodeState | None:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_config_sync_pre_v11([[["0 - Synchronized"]]])
    NodeState(state='0', description='Synchronized')
    """
    return NodeState(*string_table[0][0][0].split(" - ", 1)) if string_table[0] else None


# see: 1.3.6.1.4.1.3375.2.1.1.1.1.6.0
# F5-BIGIP-SYSTEM-MIB::sysAttrConfigsyncState (STRING)
# "-1 - uninitialized or disabled config state"

# F5 nodes need to be ntp synced otherwise status reports might be wrong.


def check_f5_bigip_config_sync_pre_v11(section: NodeState) -> CheckResult:
    # possible state values:
    #  -1   unconfigured,           ok only if original status
    #                               otherwise this would mean something is heavily broken?
    #   0   in sync,                ok
    # 1/2   one system outdated,    warn
    #   3   both systems outdated,  crit   (config split brain)
    if section.state == "0":
        yield Result(state=State.OK, summary=section.description)
    elif section.state in {"-1", "3"}:
        yield Result(state=State.CRIT, summary=section.description)
    elif section.state in {"1", "2"}:
        yield Result(state=State.WARN, summary=section.description)
    else:
        yield Result(
            state=State.UNKNOWN,
            summary="unexpected output from SNMP Agent %r" % section.description,
        )


snmp_section_f5_bigip_cluster = SNMPSection(
    name="f5_bigip_cluster",
    detect=all_of(F5_BIGIP, VERSION_PRE_V11),
    parse_function=parse_f5_bigip_config_sync_pre_v11,
    fetch=[
        SNMPTree(base=".1.3.6.1.4.1.3375.2.1.1.1.1", oids=["6"]),  # sysAttrConfigsyncState
    ],
)

check_plugin_f5_bigip_cluster = CheckPlugin(
    name="f5_bigip_cluster",  # name taken from pre-1.7 plug-in
    service_name="Config Sync status",
    discovery_function=discover_f5_bigip_config_sync,
    check_function=check_f5_bigip_config_sync_pre_v11,
)

# Agent / MIB output
# see: .1.3.6.1.4.1.3375.2.1.14.1.1.0
#      .1.3.6.1.4.1.3375.2.1.14.1.2.0
# F5-BIGIP-SYSTEM-MIB::sysCmSyncStatusId
# F5-BIGIP-SYSTEM-MIB::sysCmSyncStatusStatus

# F5 nodes need to be ntp synced otherwise status reports might be wrong.


def parse_f5_bigip_config_sync_v11_plus(string_table: Sequence[StringTable]) -> NodeState | None:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_config_sync_v11_plus([[['3', 'In Sync']]])
    NodeState(state='3', description='In Sync')
    """
    return NodeState(*string_table[0][0]) if string_table[0] else None


def check_f5_bigip_config_sync_v11_plus(
    params: Mapping[str, int], section: NodeState
) -> CheckResult:
    """
    >> for r in check_f5_bigip_config_sync_v11_plus(
    ...         params=CONFIG_SYNC_DEFAULT_PARAMETERS,
    ...         section={"node1": 0, "node2": 3}):
    ...     print(r)
    Result(state=<State.OK: 0>, summary='Node [node1] is standby')
    """
    param_key, status_name = CONFIG_SYNC_STATES[section.state]
    status = params.get(param_key, CONFIG_SYNC_DEFAULT_PARAMETERS[param_key])
    infotext = status_name
    if status_name != section.description:
        infotext += " - " + section.description
    yield Result(state=State(status), summary=infotext)


snmp_section_f5_bigip_cluster_v11 = SNMPSection(
    name="f5_bigip_cluster_v11",
    detect=all_of(F5_BIGIP, VERSION_V11_PLUS),
    parse_function=parse_f5_bigip_config_sync_v11_plus,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.14.1",
            oids=[
                "1.0",  # sysCmSyncStatusId
                "2.0",  # sysCmSyncStatusStatus
            ],
        ),
    ],
)

check_plugin_f5_bigip_cluster_v11 = CheckPlugin(
    name="f5_bigip_cluster_v11",  # name taken from pre-1.7 plug-in
    service_name="Config Sync status",
    discovery_function=discover_f5_bigip_config_sync,
    check_function=check_f5_bigip_config_sync_v11_plus,
    check_default_parameters=CONFIG_SYNC_DEFAULT_PARAMETERS,
    check_ruleset_name="f5_bigip_cluster_v11",
)
