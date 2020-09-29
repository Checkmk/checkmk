#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple
import functools
from typing import (
    Iterable,
    Generator,
    List,
    Mapping,
    MutableMapping,
    Optional,
)
from .agent_based_api.v1 import (
    register,
    Result,
    Service,
    State as state,
    type_defs,
)
from .agent_based_api.v1.clusterize import aggregate_node_details

# <<<veritas_vcs>>>
# ClusState        RUNNING
# ClusterName      minions
# #System          Attribute      Value
# dave             SysState       RUNNING
# stuart           SysState       RUNNING
# #Group           Attribute      System      Value
# ClusterService   State          stuart      |OFFLINE|
# nepharius        State          stuart      |ONLINE|
# lan              State          stuart      |ONLINE|
# omd              State          stuart      |ONLINE|
# #Resource        Attribute      System       Value
# nepharius_mrs    State          stuart      ONLINE
# nepharius_dr     State          stuart      ONLINE
# cs_ip            State          stuart      OFFLINE
# cs_proxy         State          stuart      ONLINE
# lan_nic          State          stuart      ONLINE
# lan_phantom      State          stuart      ONLINE
# omd_apache       State          stuart      ONLINE
# omd_appl         State          stuart      ONLINE
# omd_dg           State          stuart      ONLINE
# omd_proxy        State          stuart      ONLINE
# omd_srdf         State          stuart      ONLINE
# omd_uc4ps1_agt   State          stuart      ONLINE
# omdp_ip          State          stuart      ONLINE
# omdp_mnt         State          stuart      ONLINE
# #Group           Attribute      System      Value
# ClusterService   Frozen         global      0
# ClusterService   TFrozen        global      0
# #
# nepharius        Frozen         global      0
# nepharius        TFrozen        global      1
# #
# lan              Frozen         global      0
# lan              TFrozen        global      0
# #
# omd              Frozen         global      1
# omd              TFrozen        global      0

# parsed section:
# section = {
#    'cluster': {u'minions': [('ClusState', 'RUNNING', None)]},
#    u'group': {u'ClusterService': [('State', 'OFFLINE', 'minions'),
#                                  ('Frozen', '0', 'minions'),
#                                  ('TFrozen', '0', 'minions')],
#              u'lan': [('State', 'ONLINE', 'minions'),
#                       ('Frozen', '0', 'minions'),
#                       ('TFrozen', '0', 'minions')],
#              u'nepharius': [('State', 'ONLINE', 'minions'),
#                             ('Frozen', '0', 'minions'),
#                             ('TFrozen', '1', 'minions')],
#              u'omd': [('State', 'ONLINE', 'minions'),
#                       ('Frozen', '1', 'minions'),
#                       ('TFrozen', '0', 'minions')]},
#    u'resource': {u'cs_ip': [('State', 'OFFLINE', 'minions')],
#                  u'cs_proxy': [('State', 'ONLINE', 'minions')],
#                  u'lan_nic': [('State', 'ONLINE', 'minions')],
#                  u'lan_phantom': [('State', 'ONLINE', 'minions')],
#                  u'nepharius_dr': [('State', 'ONLINE', 'minions')],
#                  u'nepharius_mrs': [('State', 'ONLINE', 'minions')],
#                  u'omd_apache': [('State', 'ONLINE', 'minions')],
#                  u'omd_appl': [('State', 'ONLINE', 'minions')],
#                  u'omd_dg': [('State', 'ONLINE', 'minions')],
#                  u'omd_proxy': [('State', 'ONLINE', 'minions')],
#                  u'omd_srdf': [('State', 'ONLINE', 'minions')],
#                  u'omd_uc4ps1_agt': [('State', 'ONLINE', 'minions')],
#                  u'omdp_ip': [('State', 'ONLINE', 'minions')],
#                  u'omdp_mnt': [('State', 'ONLINE', 'minions')]},
#    u'system': {u'dave': [('SysState', 'RUNNING', 'minions')],
#                u'stuart': [('SysState', 'RUNNING', 'minions')]}}

# Possible values for ClusState: RUNNING
# Possible values for SysState: RUNNING, FAULTED, EXITED
# Possible values for SG State: ONLINE, OFFLINE, FAULTED
# Possible values for resource State: ONLINE, OFFLINE, FAULTED, OFFLINE|STATE UNKNOWN, ONLINE|STATE UNKNOWN
# the STATE UNKNOWN is treated as UNKNOWN
#
#  NOTE: It seems to me there are way more possible values.
#        In the older version, all of these go to WARN(1).
#        We keep it that way, but make it configurable.

CHECK_DEFAULT_PARAMETERS = {
    'map_frozen': {
        'tfrozen': 1,
        'frozen': 2,
    },
    'map_states': {
        "ONLINE": 0,
        "RUNNING": 0,
        "OK": 0,
        "OFFLINE": 1,
        "EXITED": 1,
        "PARTIAL": 1,
        "FAULTED": 2,
        "UNKNOWN": 3,
        "default": 1,
    },
}

Vcs = namedtuple("Vcs", ["attr", "value", "cluster"])
SubSection = MutableMapping[str, List[Vcs]]
Section = MutableMapping[str, SubSection]
ClusterSection = Mapping[str, Section]


def parse_veritas_vcs(string_table: type_defs.AgentStringTable) -> Optional[Section]:
    parsed: Section = {}

    for line in string_table:
        if line == ['#']:
            continue

        if line[0] == "ClusState":
            section = parsed.setdefault('cluster', {})
            attr = line[0]
            value = line[1]

        elif line[0] == "ClusterName":
            cluster_name = line[1]
            section.setdefault(cluster_name, []).append(Vcs(attr, value, None))

        elif line[0].startswith('#'):
            section = parsed.setdefault(line[0][1:].lower(), {})
            attr_idx = line.index('Attribute')
            value_idx = line.index('Value')

        elif len(line) > 2:
            item_name = line[0]
            attr = line[attr_idx]
            value = line[value_idx].replace("|", "")
            if "UNKNOWN" in value:
                value = "UNKNOWN"
            section.setdefault(item_name, []).append(Vcs(attr, value, cluster_name))

    return parsed or None


register.agent_section(
    name="veritas_vcs",
    parse_function=parse_veritas_vcs,
)


def discover_veritas_vcs_subsection(subsection: SubSection,) -> type_defs.DiscoveryResult:
    for item_name in subsection:
        yield Service(item=item_name)


def veritas_vcs_boil_down_states_in_cluster(states: Iterable[str]) -> str:
    _stat = set(states)
    if len(_stat) == 1:
        return _stat.pop()
    for dominant in ("FAULTED", "UNKNOWN", "ONLINE", "RUNNING"):
        if dominant in _stat:
            return dominant
    return "AGGREGATION: %s" % ', '.join(sorted(_stat))


def check_veritas_vcs_subsection(
    item: str,
    params: type_defs.Parameters,
    subsection: SubSection,
) -> Generator[Result, None, None]:
    list_vcs_tuples = subsection.get(item)
    if list_vcs_tuples is None:
        return  # vanished

    map_frozen = params['map_frozen']
    map_states = params['map_states']

    infotexts = []
    for vcs in list_vcs_tuples:
        if vcs.attr.endswith('State'):
            infotexts.append(vcs.value.lower())

        if vcs.attr.endswith('Frozen') and vcs.value != '0':
            frozen_txt = vcs.attr.lower().replace('t', 'temporarily ').lower()
            yield Result(
                state=state(map_frozen.get(vcs.attr.lower(), 3)),
                summary=frozen_txt,
            )

    states = (vcs.value for vcs in list_vcs_tuples if vcs.attr.endswith('State'))
    state_txt = veritas_vcs_boil_down_states_in_cluster(states)
    state_int = map_states.get(state_txt, map_states['default'])
    yield Result(
        state=state(state_int),
        summary="%s" % ", ".join(infotexts),
    )

    # get last not None cluster name
    cluster_name = functools.reduce(lambda x, y: y if y.cluster else x, list_vcs_tuples).cluster
    if cluster_name is not None:
        yield Result(
            state=state.OK,
            summary="cluster: %s" % cluster_name,
        )


def cluster_check_veritas_vcs_subsection(
    item: str,
    params: type_defs.Parameters,
    subsections: Mapping[str, SubSection],
) -> type_defs.CheckResult:
    last_cluster_result = None

    all_nodes_ok = True

    for node_name, node_subsec in subsections.items():
        node_results = list(check_veritas_vcs_subsection(item, params, node_subsec))
        if not node_results:
            continue

        if node_results[-1].summary.startswith('cluster: '):
            last_cluster_result = node_results[-1]
            node_results = node_results[:-1]

        agg_node_state, agg_node_text = aggregate_node_details(
            node_name,
            node_results,
        )
        if agg_node_text:
            details_prefix = "[%s]: " % node_name
            details_split = agg_node_text.split('\n')
            details_split = [details_split[0]] + [
                detail_split[len(details_prefix):] for detail_split in details_split[1:]
            ]
            yield Result(
                state=agg_node_state,
                notice=', '.join(details_split),
                details=agg_node_text,
            )
            all_nodes_ok &= agg_node_state is state.OK

    if all_nodes_ok:
        yield Result(
            state=state.OK,
            summary='All nodes OK',
        )

    if last_cluster_result:
        yield last_cluster_result


#   .--cluster - main check -----------------------------------------------.
#   |                         _           _                                |
#   |                     ___| |_   _ ___| |_ ___ _ __                     |
#   |                    / __| | | | / __| __/ _ \ '__|                    |
#   |                   | (__| | |_| \__ \ ||  __/ |                       |
#   |                    \___|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_veritas_vcs(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get('cluster', {}))


def check_veritas_vcs(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get('cluster', {}),
    )


def cluster_check_veritas_vcs(
    item: str,
    params: type_defs.Parameters,
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {node_name: node_section.get('cluster', {}) for node_name, node_section in section.items()},
    )


register.check_plugin(
    name="veritas_vcs",
    sections=['veritas_vcs'],
    service_name="VCS Cluster %s",
    discovery_function=discover_veritas_vcs,
    check_ruleset_name='veritas_vcs',
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs,
    cluster_check_function=cluster_check_veritas_vcs,
)

#.
#   .--system--------------------------------------------------------------.
#   |                                 _                                    |
#   |                   ___ _   _ ___| |_ ___ _ __ ___                     |
#   |                  / __| | | / __| __/ _ \ '_ ` _ \                    |
#   |                  \__ \ |_| \__ \ ||  __/ | | | | |                   |
#   |                  |___/\__, |___/\__\___|_| |_| |_|                   |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_system(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get('system', {}))


def check_veritas_vcs_system(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get('system', {}),
    )


def cluster_check_veritas_vcs_system(
    item: str,
    params: type_defs.Parameters,
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {node_name: node_section.get('system', {}) for node_name, node_section in section.items()},
    )


register.check_plugin(
    name="veritas_vcs_system",
    sections=['veritas_vcs'],
    service_name="VCS System %s",
    discovery_function=discover_veritas_vcs_system,
    check_ruleset_name='veritas_vcs',
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_system,
    cluster_check_function=cluster_check_veritas_vcs_system,
)

#.
#   .--service group-------------------------------------------------------.
#   |                        _                                             |
#   |    ___  ___ _ ____   _(_) ___ ___    __ _ _ __ ___  _   _ _ __       |
#   |   / __|/ _ \ '__\ \ / / |/ __/ _ \  / _` | '__/ _ \| | | | '_ \      |
#   |   \__ \  __/ |   \ V /| | (_|  __/ | (_| | | | (_) | |_| | |_) |     |
#   |   |___/\___|_|    \_/ |_|\___\___|  \__, |_|  \___/ \__,_| .__/      |
#   |                                     |___/                |_|         |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_group(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get('group', {}))


def check_veritas_vcs_group(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get('group', {}),
    )


def cluster_check_veritas_vcs_group(
    item: str,
    params: type_defs.Parameters,
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {node_name: node_section.get('group', {}) for node_name, node_section in section.items()},
    )


register.check_plugin(
    name="veritas_vcs_servicegroup",
    sections=['veritas_vcs'],
    service_name="VCS Service Group %s",
    discovery_function=discover_veritas_vcs_group,
    check_ruleset_name='veritas_vcs',
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_group,
    cluster_check_function=cluster_check_veritas_vcs_group,
)

#.
#   .--resource------------------------------------------------------------.
#   |                                                                      |
#   |               _ __ ___  ___  ___  _   _ _ __ ___ ___                 |
#   |              | '__/ _ \/ __|/ _ \| | | | '__/ __/ _ \                |
#   |              | | |  __/\__ \ (_) | |_| | | | (_|  __/                |
#   |              |_|  \___||___/\___/ \__,_|_|  \___\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_resource(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get('resource', {}))


def check_veritas_vcs_resource(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get('resource', {}),
    )


def cluster_check_veritas_vcs_resource(
    item: str,
    params: type_defs.Parameters,
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {
            node_name: node_section.get('resource', {})
            for node_name, node_section in section.items()
        },
    )


register.check_plugin(
    name="veritas_vcs_resource",
    sections=['veritas_vcs'],
    service_name="VCS Resource %s",
    discovery_function=discover_veritas_vcs_resource,
    check_ruleset_name='veritas_vcs',
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_resource,
    cluster_check_function=cluster_check_veritas_vcs_resource,
)
