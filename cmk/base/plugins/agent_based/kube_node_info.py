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
from cmk.base.plugins.agent_based.utils.kube import (
    kube_annotations_to_cmk_labels,
    kube_labels_to_cmk_labels,
    NodeInfo,
)
from cmk.base.plugins.agent_based.utils.kube_info import check_info


def parse_kube_node_info(string_table: StringTable):
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
    ... '"annotations": {}'
    ... '}'
    ... ]])
    NodeInfo(architecture='amd64', kernel_version='5.13.0-27-generic', os_image='Ubuntu 20.04.2 LTS', operating_system='linux', container_runtime_version='docker://20.10.8', name='minikube', creation_timestamp=1640000000.0, labels={}, annotations={}, addresses=[], cluster='cluster')
    """
    return NodeInfo(**json.loads(string_table[0][0]))


def host_labels(section: NodeInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
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

    """
    yield HostLabel("cmk/kubernetes/object", "node")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    yield HostLabel("cmk/kubernetes/node", section.name)
    yield HostLabel("cmk/os_family", section.operating_system)
    yield from kube_labels_to_cmk_labels(section.labels)
    yield from kube_annotations_to_cmk_labels(section.annotations)


register.agent_section(
    name="kube_node_info_v1",
    parsed_section_name="kube_node_info",
    parse_function=parse_kube_node_info,
    host_label_function=host_labels,
)


def discovery_kube_node_info(section: NodeInfo) -> DiscoveryResult:
    yield Service()


def check_kube_node_info(section: NodeInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "creation_timestamp": section.creation_timestamp,
            "os_image": section.os_image,
            "container_runtime_version": section.container_runtime_version,
            "architecture": section.architecture,
            "kernel_version": section.kernel_version,
            "operating_system": section.operating_system,
        }
    )


register.check_plugin(
    name="kube_node_info",
    service_name="Info",
    discovery_function=discovery_kube_node_info,
    check_function=check_kube_node_info,
)
