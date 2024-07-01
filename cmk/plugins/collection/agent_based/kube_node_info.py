#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Service,
    StringTable,
)
from cmk.plugins.kube.schemata.section import NodeInfo
from cmk.plugins.lib.kube import (
    check_with_time,
    kube_annotations_to_cmk_labels,
    kube_labels_to_cmk_labels,
)
from cmk.plugins.lib.kube_info import check_info


def parse_kube_node_info(string_table: StringTable) -> NodeInfo:
    """Parses `string_table` into a NodeInfo instance

    >>> parse_kube_node_info([['{"architecture": "amd64",'
    ... '"name": "minikube",'
    ... '"kernel_version": "5.13.0-27-generic",'
    ... '"os_image": "Ubuntu 20.04.2 LTS",'
    ... '"operating_system": "linux",'
    ... '"creation_timestamp": "1640000000.0",'
    ... '"container_runtime_version": "docker://20.10.8",'
    ... '"addresses": [],'
    ... '"cluster": "cluster",'
    ... '"labels": {},'
    ... '"annotations": {},'
    ... '"kubernetes_cluster_hostname": "host"'
    ... '}'
    ... ]])
    NodeInfo(architecture='amd64', kernel_version='5.13.0-27-generic', os_image='Ubuntu 20.04.2 LTS', operating_system='linux', container_runtime_version='docker://20.10.8', name='minikube', creation_timestamp=1640000000.0, labels={}, annotations={}, addresses=[], cluster='cluster', kubernetes_cluster_hostname='host')
    """
    return NodeInfo.model_validate_json(string_table[0][0])


def host_labels(section: NodeInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes:
            This label is set to "yes" for all Kubernetes objects.

        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.

        cmk/kubernetes/node:
            This label contains the name of the Kubernetes Node this checkmk
            host is associated with. Checkmk hosts of the type Pod and Node
            will be assigned this label.

        cmk/kubernetes/annotation/{key}:{value} :
            These labels are yielded for each Kubernetes annotation that is
            a valid Kubernetes label. This can be configured via the rule
            'Kubernetes'.

        cmk/os_family:
            This label is set to the operating system as reported by the agent
            as "AgentOS" (such as "windows" or "linux").

        cmk/kubernetes/cluster-host:
            This label contains the name of the Checkmk host which represents the
            Kubernetes cluster.

    """
    yield HostLabel("cmk/kubernetes", "yes")
    yield HostLabel("cmk/kubernetes/object", "node")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    yield HostLabel("cmk/kubernetes/node", section.name)
    yield HostLabel("cmk/os_family", section.operating_system)
    yield HostLabel("cmk/kubernetes/cluster-host", section.kubernetes_cluster_hostname)
    yield from kube_labels_to_cmk_labels(section.labels)
    yield from kube_annotations_to_cmk_labels(section.annotations)


agent_section_kube_node_info_v1 = AgentSection(
    name="kube_node_info_v1",
    parsed_section_name="kube_node_info",
    parse_function=parse_kube_node_info,
    host_label_function=host_labels,
)


def discovery_kube_node_info(section: NodeInfo) -> DiscoveryResult:
    yield Service()


def check_kube_node_info(now: float, section: NodeInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "age": now - section.creation_timestamp,
            "os_image": section.os_image,
            "container_runtime_version": section.container_runtime_version,
            "architecture": section.architecture,
            "kernel_version": section.kernel_version,
            "operating_system": section.operating_system,
        }
    )


check_plugin_kube_node_info = CheckPlugin(
    name="kube_node_info",
    service_name="Info",
    discovery_function=discovery_kube_node_info,
    check_function=check_with_time(check_kube_node_info),
)
