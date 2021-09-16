#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP-Cluster Config Sync - SNMP sections and Checks
"""
from typing import Any, List, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import all_of, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.f5_bigip import F5_BIGIP, VERSION_PRE_V11, VERSION_V11_PLUS


class State(NamedTuple):
    state: str
    description: str


CONFIG_SYNC_DEFAULT_PARAMETERS = {
    "0": 3,
    "1": 0,
    "2": 1,
    "3": 0,
    "4": 2,
    "5": 2,
    "6": 2,
    "7": 1,
    "8": 2,
    "9": 2,
}

CONFIG_SYNC_STATE_NAMES = {
    "0": "Unknown",
    "1": "Syncing",
    "2": "Need Manual Sync",
    "3": "In Sync",
    "4": "Sync Failed",
    "5": "Sync Disconnected",
    "6": "Standalone",
    "7": "Awaiting Initial Sync",
    "8": "Incompatible Version",
    "9": "Partial Sync",
}


def discover_f5_bigip_config_sync(section: State) -> DiscoveryResult:
    # run inventory unless we found a device in unconfigured state
    # don't need to loop over the input as there's only one status
    if not section.state == "-1":
        yield Service()


def parse_f5_bigip_config_sync_pre_v11(string_table: List[StringTable]) -> Optional[State]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_config_sync_pre_v11([[["0 - Synchronized"]]])
    State(state='0', description='Synchronized')
    """
    return State(*string_table[0][0][0].split(" - ", 1)) if string_table[0] else None


# see: 1.3.6.1.4.1.3375.2.1.1.1.1.6.0
# F5-BIGIP-SYSTEM-MIB::sysAttrConfigsyncState (STRING)
# "-1 - uninitialized or disabled config state"

# F5 nodes need to be ntp synced otherwise status reports might be wrong.


def check_f5_bigip_config_sync_pre_v11(section: State) -> CheckResult:
    # possible state values:
    #  -1   unconfigured,           ok only if original status
    #                               otherwise this would mean something is heavily broken?
    #   0   in sync,                ok
    # 1/2   one system outdated,    warn
    #   3   both systems outdated,  crit   (config split brain)
    if section.state == "0":
        yield Result(state=state.OK, summary=section.description)
    elif section.state in {"-1", "3"}:
        yield Result(state=state.CRIT, summary=section.description)
    elif section.state in {"1", "2"}:
        yield Result(state=state.WARN, summary=section.description)
    else:
        yield Result(
            state=state.UNKNOWN,
            summary="unexpected output from SNMP Agent %r" % section.description,
        )


register.snmp_section(
    name="f5_bigip_cluster",
    detect=all_of(F5_BIGIP, VERSION_PRE_V11),
    parse_function=parse_f5_bigip_config_sync_pre_v11,
    fetch=[
        SNMPTree(base=".1.3.6.1.4.1.3375.2.1.1.1.1", oids=["6"]),  # sysAttrConfigsyncState
    ],
)

register.check_plugin(
    name="f5_bigip_cluster",  # name taken from pre-1.7 plugin
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


def parse_f5_bigip_config_sync_v11_plus(string_table: List[StringTable]) -> Optional[State]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_config_sync_v11_plus([[['3', 'In Sync']]])
    State(state='3', description='In Sync')
    """
    return State(*string_table[0][0]) if string_table[0] else None


def check_f5_bigip_config_sync_v11_plus(params: Mapping[str, Any], section: State) -> CheckResult:
    """
    >> for r in check_f5_bigip_config_sync_v11_plus(
    ...         params=CONFIG_SYNC_DEFAULT_PARAMETERS,
    ...         section={"node1": 0, "node2": 3}):
    ...     print(r)
    Result(state=<state.OK: 0>, summary='Node [node1] is standby')
    """
    status = params[section.state]
    status_name = CONFIG_SYNC_STATE_NAMES[section.state]
    infotext = status_name
    if status_name != section.description:
        infotext += " - " + section.description
    yield Result(state=state(status), summary=infotext)


register.snmp_section(
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

register.check_plugin(
    name="f5_bigip_cluster_v11",  # name taken from pre-1.7 plugin
    service_name="Config Sync status",
    discovery_function=discover_f5_bigip_config_sync,
    check_function=check_f5_bigip_config_sync_v11_plus,
    check_default_parameters=CONFIG_SYNC_DEFAULT_PARAMETERS,
    check_ruleset_name="f5_bigip_cluster_v11",
)
