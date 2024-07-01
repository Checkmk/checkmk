#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.kube.schemata.section import DaemonSetInfo
from cmk.plugins.lib.kube import check_with_time
from cmk.plugins.lib.kube_info import check_info, host_labels


def parse(string_table: StringTable) -> DaemonSetInfo:
    """Parses `string_table` into a DaemonSetInfo instance

    >>> parse([[
    ... '{"name": "oh-lord",'
    ... '"namespace": "have-mercy",'
    ... '"labels": {},'
    ... '"annotations": {},'
    ... '"selector": {"match_labels": {}, "match_expressions": [{"key": "app", "operator": "In", "values": ["sleep"]}]},'
    ... '"creation_timestamp": 1638798546.0,'
    ... '"containers": {"images": ["i/name:0.5"], "names": ["name"]},'
    ... '"kubernetes_cluster_hostname": "host",'
    ... '"cluster": "cluster"}'
    ... ]])
    DaemonSetInfo(name='oh-lord', namespace='have-mercy', labels={}, annotations={}, selector=Selector(match_labels={}, match_expressions=[MatchExpression(key='app', operator='In', values=['sleep'])]), creation_timestamp=1638798546.0, containers=ThinContainers(images=frozenset({'i/name:0.5'}), names=['name']), cluster='cluster', kubernetes_cluster_hostname='host')
    """
    return DaemonSetInfo.model_validate_json(string_table[0][0])


agent_section_kube_daemonset_info_v1 = AgentSection[DaemonSetInfo](
    name="kube_daemonset_info_v1",
    parsed_section_name="kube_daemonset_info",
    parse_function=parse,
    host_label_function=host_labels("daemonset"),
)


def discovery(section: DaemonSetInfo) -> DiscoveryResult:
    yield Service()


def check_kube_daemonset_info(now: float, section: DaemonSetInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "namespace": section.namespace,
            "age": now - section.creation_timestamp,
        }
    )


check_plugin_kube_daemonset_info = CheckPlugin(
    name="kube_daemonset_info",
    service_name="Info",
    discovery_function=discovery,
    check_function=check_with_time(check_kube_daemonset_info),
)
