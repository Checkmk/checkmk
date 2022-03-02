#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel, register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.k8s import PodInfo
from cmk.base.plugins.agent_based.utils.kube import kube_labels_to_cmk_labels, KubernetesError
from cmk.base.plugins.agent_based.utils.kube_info import check_info


def parse_kube_pod_info(string_table: StringTable):
    """
    >>> parse_kube_pod_info([[
    ... '{"namespace": "redis", '
    ... '"name": "redis-xyz", '
    ... '"creation_timestamp": 1637069562.0, '
    ... '"labels": {}, '
    ... '"node": "k8-w2", '
    ... '"host_network": null, '
    ... '"dns_policy": "Default", '
    ... '"host_ip": "192.168.49.2", '
    ... '"pod_ip": "172.17.0.2", '
    ... '"qos_class": "burstable", '
    ... '"restart_policy": "Always", '
    ... '"cluster": "cluster", '
    ... '"uid": "dd1019ca-c429-46af-b6b7-8aad47b6081a", '
    ... '"controllers": [{"type_": "deployment", "name": "redis-deployment"}]}'
    ... ]])
    PodInfo(namespace='redis', name='redis-xyz', creation_timestamp=1637069562.0, labels={}, node='k8-w2', host_network=None, dns_policy='Default', host_ip='192.168.49.2', pod_ip='172.17.0.2', qos_class='burstable', restart_policy='Always', uid='dd1019ca-c429-46af-b6b7-8aad47b6081a', controllers=[Controller(type_=<ControllerType.deployment: 'deployment'>, name='redis-deployment')], cluster='cluster')
    """
    return PodInfo(**json.loads(string_table[0][0]))


def host_labels(section: PodInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.

        cmk/kubernetes/namespace:
            This label is set to the namespace of the deployment.

        cmk/kubernetes/node:
            This label is set to the node of the pod.
    """
    yield HostLabel("cmk/kubernetes/object", "pod")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    if section.node is not None:
        yield HostLabel("cmk/kubernetes/node", section.node)

    if section.namespace:
        yield HostLabel("cmk/kubernetes/namespace", section.namespace)

    for controller in section.controllers:
        yield HostLabel(f"cmk/kubernetes/{controller.type_.value}", controller.name)

    yield from kube_labels_to_cmk_labels(section.labels)


register.agent_section(
    name="kube_pod_info_v1",
    parsed_section_name="kube_pod_info",
    parse_function=parse_kube_pod_info,
    host_label_function=host_labels,
)


def discovery_kube_pod_info(section: PodInfo) -> DiscoveryResult:
    yield Service()


def check_kube_pod_info(section: PodInfo) -> CheckResult:
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
            "creation_timestamp": section.creation_timestamp,
            "qos_class": section.qos_class,
            "uid": section.uid,
            "restart_policy": section.restart_policy,
        }
    )


register.check_plugin(
    name="kube_pod_info",
    service_name="Info",
    discovery_function=discovery_kube_pod_info,
    check_function=check_kube_pod_info,
)
