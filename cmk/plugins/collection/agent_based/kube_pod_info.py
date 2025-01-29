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
from cmk.plugins.kube.schemata.section import PodInfo
from cmk.plugins.lib.kube import (
    check_with_time,
    kube_annotations_to_cmk_labels,
    kube_labels_to_cmk_labels,
    KubernetesError,
)
from cmk.plugins.lib.kube_info import check_info


def parse_kube_pod_info(string_table: StringTable) -> PodInfo:
    """
    >>> parse_kube_pod_info([[
    ... '{"namespace": "redis", '
    ... '"name": "redis-xyz", '
    ... '"creation_timestamp": 1637069562.0, '
    ... '"labels": {}, '
    ... '"annotations": {}, '
    ... '"node": "k8-w2", '
    ... '"host_network": null, '
    ... '"dns_policy": "Default", '
    ... '"host_ip": "192.168.49.2", '
    ... '"pod_ip": "172.17.0.2", '
    ... '"qos_class": "burstable", '
    ... '"restart_policy": "Always", '
    ... '"cluster": "cluster", '
    ... '"kubernetes_cluster_hostname": "host", '
    ... '"uid": "dd1019ca-c429-46af-b6b7-8aad47b6081a", '
    ... '"controllers": [{"type_": "Deployment", "name": "redis-deployment"}]}'
    ... ]])
    PodInfo(namespace='redis', name='redis-xyz', creation_timestamp=1637069562.0, labels={}, annotations={}, node='k8-w2', host_network=None, dns_policy='Default', host_ip='192.168.49.2', pod_ip='172.17.0.2', qos_class='burstable', restart_policy='Always', uid='dd1019ca-c429-46af-b6b7-8aad47b6081a', controllers=[Controller(type_='Deployment', name='redis-deployment')], cluster='cluster', kubernetes_cluster_hostname='host')
    """
    return PodInfo.model_validate_json(string_table[0][0])


def host_labels(section: PodInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes:
            This label is set to "yes" for all Kubernetes objects.

        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.

        cmk/kubernetes/namespace:
            This label contains the name of the Kubernetes Namespace this
            checkmk host is associated with.

        cmk/kubernetes/annotation/{key}:{value} :
            These labels are yielded for each Kubernetes annotation that is
            a valid Kubernetes label. This can be configured via the rule
            'Kubernetes'.

        cmk/kubernetes/node:
            This label contains the name of the Kubernetes Node this checkmk
            host is associated with. Checkmk hosts of the type Pod and Node
            will be assigned this label.


        cmk/kubernetes/cluster-host:
            This label contains the name of the Checkmk host which represents the
            Kubernetes cluster.
    """
    yield HostLabel("cmk/kubernetes", "yes")
    yield HostLabel("cmk/kubernetes/object", "pod")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    if section.node is not None:
        yield HostLabel("cmk/kubernetes/node", section.node)

    if section.namespace:
        yield HostLabel("cmk/kubernetes/namespace", section.namespace)

    for controller in section.controllers:
        yield HostLabel(f"cmk/kubernetes/{controller.type_.lower()}", controller.name)

    yield HostLabel("cmk/kubernetes/cluster-host", section.kubernetes_cluster_hostname)
    yield from kube_labels_to_cmk_labels(section.labels)
    yield from kube_annotations_to_cmk_labels(section.annotations)


agent_section_kube_pod_info_v1 = AgentSection(
    name="kube_pod_info_v1",
    parsed_section_name="kube_pod_info",
    parse_function=parse_kube_pod_info,
    host_label_function=host_labels,
)


def discovery_kube_pod_info(section: PodInfo) -> DiscoveryResult:
    yield Service()


def check_kube_pod_info(now: float, section: PodInfo) -> CheckResult:
    # To get an understanding of API objects this check deals with, one can take a look at
    # PodInfo and the definition of its fields

    if section.namespace is None:
        raise KubernetesError("Pod has no namespace")

    if section.creation_timestamp is None:
        raise KubernetesError("Pod has no creation timestamp")

    yield from check_info(
        {
            "node": section.node,
            "name": section.name,
            "namespace": section.namespace,
            "age": now - section.creation_timestamp,
            "qos_class": section.qos_class,
            "uid": section.uid,
            "restart_policy": section.restart_policy,
            "control_chain": section.controllers,
        }
    )


check_plugin_kube_pod_info = CheckPlugin(
    name="kube_pod_info",
    service_name="Info",
    discovery_function=discovery_kube_pod_info,
    check_function=check_with_time(check_kube_pod_info),
)
