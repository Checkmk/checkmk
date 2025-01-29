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
from cmk.plugins.kube.schemata.section import StatefulSetInfo
from cmk.plugins.lib.kube import check_with_time
from cmk.plugins.lib.kube_info import check_info, host_labels


def parse(string_table: StringTable) -> StatefulSetInfo:
    """Parses `string_table` into a StatefulSetInfo instance

    >>> parse([[
    ... '{"name": "oh-lord",'
    ... '"namespace": "have-mercy",'
    ... '"labels": {},'
    ... '"annotations": {},'
    ... '"selector": {"match_labels": {}, "match_expressions": [{"key": "app", "operator": "In", "values": ["sleep"]}]},'
    ... '"creation_timestamp": 1638798546.0,'
    ... '"containers": {"images": ["i/name:0.5"], "names": ["name"]},'
    ... '"kubernetes_cluster_hostname": "host",'
    ... '"cluster": "sweet-jesus"}'
    ... ]])
    StatefulSetInfo(name='oh-lord', namespace='have-mercy', labels={}, annotations={}, selector=Selector(match_labels={}, match_expressions=[MatchExpression(key='app', operator='In', values=['sleep'])]), creation_timestamp=1638798546.0, containers=ThinContainers(images=frozenset({'i/name:0.5'}), names=['name']), cluster='sweet-jesus', kubernetes_cluster_hostname='host')
    """
    return StatefulSetInfo.model_validate_json(string_table[0][0])


agent_section_kube_statefulset_info_v1 = AgentSection(
    name="kube_statefulset_info_v1",
    parsed_section_name="kube_statefulset_info",
    parse_function=parse,
    host_label_function=host_labels("statefulset"),
)


def discovery(section: StatefulSetInfo) -> DiscoveryResult:
    yield Service()


def check_kube_statefulset_info(now: float, section: StatefulSetInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "namespace": section.namespace,
            "age": now - section.creation_timestamp,
        }
    )


check_plugin_kube_statefulset_info = CheckPlugin(
    name="kube_statefulset_info",
    service_name="Info",
    discovery_function=discovery,
    check_function=check_with_time(check_kube_statefulset_info),
)
