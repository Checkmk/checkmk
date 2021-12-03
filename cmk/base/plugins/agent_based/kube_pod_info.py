#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    HostLabel,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.k8s import PodInfo
from cmk.base.plugins.agent_based.utils.kube import KubernetesError


def parse_kube_pod_info(string_table: StringTable):
    """
    >>> parse_kube_pod_info([[
    ... '{"namespace": "redis", '
    ... '"creation_timestamp": 1637069562.0, '
    ... '"labels": {}, '
    ... '"node": "k8-w2", '
    ... '"qos_class": "burstable", '
    ... '"restart_policy": "Always", '
    ... '"uid": "dd1019ca-c429-46af-b6b7-8aad47b6081a"}'
    ... ]])
    PodInfo(namespace='redis', creation_timestamp=1637069562.0, labels={}, node='k8-w2', qos_class='burstable', restart_policy='Always', uid='dd1019ca-c429-46af-b6b7-8aad47b6081a')
    """
    return PodInfo(**json.loads(string_table[0][0]))


def host_labels(section: PodInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes/namespace:
            This label is set to the namespace of the deployment.

        cmk/kubernetes/node:
            This label is set to the node of the pod.
    """
    yield HostLabel("cmk/kubernetes/node", section.node)
    yield HostLabel("cmk/kubernetes/namespace", section.namespace)

    for label in section.labels.values():
        yield HostLabel(label.name, label.value)


register.agent_section(
    name="kube_pod_info_v1",
    parsed_section_name="kube_pod_info",
    parse_function=parse_kube_pod_info,
    host_label_function=host_labels,
)


def discovery_kube_pod_info(section: PodInfo) -> DiscoveryResult:
    yield Service()


_DETAILS_ONLY = (
    "qos_class",
    "uid",
    "restart_policy",
)

_DISPLAY_NAME = {
    "node": "Node",
    "namespace": "Namespace",
    "qos_class": "QoS class",
    "uid": "UID",
    "creation_timestamp": "Age",
    "restart_policy": "Restart policy",
}


def check_kube_pod_info(section: PodInfo) -> CheckResult:
    # To get an understanding of API objects this check deals with, one can take a look at
    # PodInfo and the definition of its fields

    if section.namespace is None:
        raise KubernetesError("Pod has no namespace")

    if section.creation_timestamp is None:
        raise KubernetesError("Pod has no creation timestamp")

    yield Result(state=State.OK, summary=f"{_DISPLAY_NAME['node']}: {section.node}")
    yield Result(state=State.OK, summary=f"{_DISPLAY_NAME['namespace']}: {section.namespace}")
    yield Result(
        state=State.OK,
        summary=f"{_DISPLAY_NAME['creation_timestamp']}: "
        f"{render.timespan(time.time() - section.creation_timestamp)}",
    )

    for field_name in _DETAILS_ONLY:
        yield Result(
            state=State.OK, notice=f"{_DISPLAY_NAME[field_name]}: {getattr(section, field_name)}"
        )


register.check_plugin(
    name="kube_pod_info",
    service_name="Pod Info",
    discovery_function=discovery_kube_pod_info,
    check_function=check_kube_pod_info,
)
