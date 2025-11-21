#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.section import ClusterInfo


def parse_kube_cluster_info(string_table: StringTable) -> ClusterInfo:
    """
    >>> parse_kube_cluster_info([[
    ... '{"name": "cluster", "version": "v1.22.2"}'
    ... ]])
    ClusterInfo(name='cluster', version='v1.22.2')
    """
    return ClusterInfo.model_validate_json(string_table[0][0])


def host_labels(section: ClusterInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes:
            This label is set to "yes" for all Kubernetes objects.

        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.
    """
    yield HostLabel("cmk/kubernetes", "yes")
    yield HostLabel("cmk/kubernetes/object", "cluster")
    yield HostLabel("cmk/kubernetes/cluster", section.name)


agent_section_kube_cluster_info_v1 = AgentSection(
    name="kube_cluster_info_v1",
    parsed_section_name="kube_cluster_info",
    parse_function=parse_kube_cluster_info,
    host_label_function=host_labels,
)


def discovery_kube_cluster_info(section: ClusterInfo) -> DiscoveryResult:
    yield Service()


def check_kube_cluster_info(section: ClusterInfo) -> CheckResult:
    yield Result(state=State.OK, summary=f"Name: {section.name}")


check_plugin_kube_cluster_info = CheckPlugin(
    name="kube_cluster_info",
    service_name="Info",
    discovery_function=discovery_kube_cluster_info,
    check_function=check_kube_cluster_info,
)
