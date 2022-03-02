#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from typing import (
    Any,
    Generator,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
)

from .agent_based_api.v1 import register, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs

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
    "map_frozen": {
        "tfrozen": 1,
        "frozen": 2,
    },
    "map_states": {
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


class Vcs(NamedTuple):
    attr: str
    value: str
    cluster: Optional[str]


SubSection = MutableMapping[str, List[Vcs]]
Section = MutableMapping[str, SubSection]
ClusterSection = Mapping[str, Optional[Section]]


class ClusterNodeResults(NamedTuple):
    node_name: str
    node_state_text: str
    node_frozen_state: state
    node_summaries: Sequence[str]


def parse_veritas_vcs(string_table: type_defs.StringTable) -> Optional[Section]:
    parsed: Section = {}

    for line in string_table:
        if line == ["#"]:
            continue

        if line[0] == "ClusState":
            section = parsed.setdefault("cluster", {})
            attr = line[0]
            value = line[1]

        elif line[0] == "ClusterName":
            cluster_name = line[1]
            section.setdefault(cluster_name, []).append(Vcs(attr, value, None))

        elif line[0].startswith("#"):
            section = parsed.setdefault(line[0][1:].lower(), {})
            attr_idx = line.index("Attribute")
            value_idx = line.index("Value")

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


def discover_veritas_vcs_subsection(
    subsection: SubSection,
) -> type_defs.DiscoveryResult:
    for item_name in subsection:
        yield Service(item=item_name)


def veritas_vcs_boil_down_states_in_cluster(states: Sequence[str]) -> str:
    if len(states) == 1:
        return states[0]
    for dominant in ("FAULTED", "UNKNOWN", "ONLINE", "RUNNING"):
        if dominant in states:
            return dominant
    return "default"


def _frozen_state_results(
    list_vcs_tuples: Sequence[Vcs], state_mapping: Mapping[str, int]
) -> Iterable[Result]:
    frozen_states = (
        vcs.attr.lower()
        for vcs in list_vcs_tuples
        if vcs.attr.endswith("Frozen") and vcs.value != "0"
    )
    yield from (
        Result(state=state(state_mapping.get(s, state(3))), summary=s.replace("t", "temporarily "))
        for s in frozen_states
    )


def _cluster_name(list_vcs_tuples: Sequence[Vcs]) -> Optional[str]:
    # get last not None cluster name
    return functools.reduce(lambda x, y: y if y.cluster else x, list_vcs_tuples).cluster


def check_veritas_vcs_subsection(
    item: str,
    params: Mapping[str, Any],
    subsection: SubSection,
) -> Generator[Result, None, None]:
    list_vcs_tuples = subsection.get(item)
    if list_vcs_tuples is None:
        return  # vanished

    yield from (_frozen_state_results(list_vcs_tuples, params["map_frozen"]))

    state_mapping = params["map_states"]
    states = [vcs.value for vcs in list_vcs_tuples if vcs.attr.endswith("State")]
    state_text = veritas_vcs_boil_down_states_in_cluster(states)
    yield Result(
        state=state(state_mapping.get(state_text, state_mapping["default"])),
        summary=", ".join(map(lambda s: s.lower(), states)),
    )

    cluster_name = _cluster_name(list_vcs_tuples)
    if cluster_name is not None:
        yield Result(
            state=state.OK,
            summary="cluster: %s" % cluster_name,
        )


def cluster_check_veritas_vcs_subsection(
    item: str,
    params: Mapping[str, Any],
    subsections: Mapping[str, SubSection],
) -> type_defs.CheckResult:

    cluster_name = None
    node_results = []
    for node_name, node_subsec in subsections.items():
        if not (item_subsection := node_subsec.get(item)):
            continue

        node_summaries = []

        node_frozen_state = state.OK
        if frozen_results := list(_frozen_state_results(item_subsection, params["map_frozen"])):
            node_frozen_state = state.worst(*(f.state for f in frozen_results))
            node_summaries.extend([f.summary for f in frozen_results])

        node_state_text = veritas_vcs_boil_down_states_in_cluster(
            [vcs.value for vcs in item_subsection if vcs.attr.endswith("State")]
        )
        node_summaries.append(node_state_text.lower())

        node_results.append(
            ClusterNodeResults(
                node_name=node_name,
                node_state_text=node_state_text,
                node_frozen_state=node_frozen_state,
                node_summaries=node_summaries,
            )
        )

        cluster_name = _cluster_name(item_subsection) or cluster_name

    if not node_results:
        return

    state_mapping = params["map_states"]
    cluster_state = state.worst(
        state(
            state_mapping.get(
                veritas_vcs_boil_down_states_in_cluster([n.node_state_text for n in node_results]),
                state_mapping["default"],
            )
        ),
        *(n.node_frozen_state for n in node_results),
    )

    if cluster_state is state.OK:
        yield Result(
            state=state.OK,
            summary="All nodes OK",
        )

    yield Result(
        state=cluster_state,
        notice=", ".join((f'[{n.node_name}]: {", ".join(n.node_summaries)}' for n in node_results)),
    )

    if cluster_name:
        yield Result(
            state=state.OK,
            summary=f"cluster: {cluster_name}",
        )


#   .--cluster - main check -----------------------------------------------.
#   |                         _           _                                |
#   |                     ___| |_   _ ___| |_ ___ _ __                     |
#   |                    / __| | | | / __| __/ _ \ '__|                    |
#   |                   | (__| | |_| \__ \ ||  __/ |                       |
#   |                    \___|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_veritas_vcs(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get("cluster", {}))


def check_veritas_vcs(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get("cluster", {}),
    )


def cluster_check_veritas_vcs(
    item: str,
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {
            node_name: node_section.get("cluster", {})
            for node_name, node_section in section.items()
            if node_section is not None
        },
    )


register.check_plugin(
    name="veritas_vcs",
    sections=["veritas_vcs"],
    service_name="VCS Cluster %s",
    discovery_function=discover_veritas_vcs,
    check_ruleset_name="veritas_vcs",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs,
    cluster_check_function=cluster_check_veritas_vcs,
)

# .
#   .--system--------------------------------------------------------------.
#   |                                 _                                    |
#   |                   ___ _   _ ___| |_ ___ _ __ ___                     |
#   |                  / __| | | / __| __/ _ \ '_ ` _ \                    |
#   |                  \__ \ |_| \__ \ ||  __/ | | | | |                   |
#   |                  |___/\__, |___/\__\___|_| |_| |_|                   |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_system(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get("system", {}))


def check_veritas_vcs_system(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get("system", {}),
    )


def cluster_check_veritas_vcs_system(
    item: str,
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {
            node_name: node_section.get("system", {})
            for node_name, node_section in section.items()
            if node_section is not None
        },
    )


register.check_plugin(
    name="veritas_vcs_system",
    sections=["veritas_vcs"],
    service_name="VCS System %s",
    discovery_function=discover_veritas_vcs_system,
    check_ruleset_name="veritas_vcs",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_system,
    cluster_check_function=cluster_check_veritas_vcs_system,
)

# .
#   .--service group-------------------------------------------------------.
#   |                        _                                             |
#   |    ___  ___ _ ____   _(_) ___ ___    __ _ _ __ ___  _   _ _ __       |
#   |   / __|/ _ \ '__\ \ / / |/ __/ _ \  / _` | '__/ _ \| | | | '_ \      |
#   |   \__ \  __/ |   \ V /| | (_|  __/ | (_| | | | (_) | |_| | |_) |     |
#   |   |___/\___|_|    \_/ |_|\___\___|  \__, |_|  \___/ \__,_| .__/      |
#   |                                     |___/                |_|         |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_group(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get("group", {}))


def check_veritas_vcs_group(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get("group", {}),
    )


def cluster_check_veritas_vcs_group(
    item: str,
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {
            node_name: node_section.get("group", {})
            for node_name, node_section in section.items()
            if node_section is not None
        },
    )


register.check_plugin(
    name="veritas_vcs_servicegroup",
    sections=["veritas_vcs"],
    service_name="VCS Service Group %s",
    discovery_function=discover_veritas_vcs_group,
    check_ruleset_name="veritas_vcs",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_group,
    cluster_check_function=cluster_check_veritas_vcs_group,
)

# .
#   .--resource------------------------------------------------------------.
#   |                                                                      |
#   |               _ __ ___  ___  ___  _   _ _ __ ___ ___                 |
#   |              | '__/ _ \/ __|/ _ \| | | | '__/ __/ _ \                |
#   |              | | |  __/\__ \ (_) | |_| | | | (_|  __/                |
#   |              |_|  \___||___/\___/ \__,_|_|  \___\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_veritas_vcs_resource(section: Section) -> type_defs.DiscoveryResult:
    yield from discover_veritas_vcs_subsection(section.get("resource", {}))


def check_veritas_vcs_resource(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from check_veritas_vcs_subsection(
        item,
        params,
        section.get("resource", {}),
    )


def cluster_check_veritas_vcs_resource(
    item: str,
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_veritas_vcs_subsection(
        item,
        params,
        {
            node_name: node_section.get("resource", {})
            for node_name, node_section in section.items()
            if node_section is not None
        },
    )


register.check_plugin(
    name="veritas_vcs_resource",
    sections=["veritas_vcs"],
    service_name="VCS Resource %s",
    discovery_function=discover_veritas_vcs_resource,
    check_ruleset_name="veritas_vcs",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_veritas_vcs_resource,
    cluster_check_function=cluster_check_veritas_vcs_resource,
)
