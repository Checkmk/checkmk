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
from cmk.base.plugins.agent_based.utils.k8s import DeploymentInfo
from cmk.base.plugins.agent_based.utils.kube_info import check_info


def parse(string_table: StringTable) -> DeploymentInfo:
    """Parses `string_table` into a DeploymentInfo instance
    >>> parse([[
    ... '{"name": "oh-lord",'
    ... '"namespace": "have-mercy",'
    ... '"labels": {},'
    ... '"selector": {"match_labels": {}, "match_expressions": [{"key": "app", "operator": "In", "values": ["sleep"]}]},'
    ... '"creation_timestamp": 1638798546.0,'
    ... '"images": ["i/name:0.5"],'
    ... '"containers": ["name"],'
    ... '"cluster": "cluster"}'
    ... ]])
    DeploymentInfo(name='oh-lord', namespace='have-mercy', labels={}, selector=Selector(match_labels={}, match_expressions=[{'key': 'app', 'operator': 'In', 'values': ['sleep']}]), creation_timestamp=1638798546.0, images=['i/name:0.5'], containers=['name'], cluster='cluster')
    """
    return DeploymentInfo(**json.loads(string_table[0][0]))


def host_labels(section: DeploymentInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.

        cmk/kubernetes/namespace:
            This label is set to the namespace of the deployment.

        cmk/kubernetes/deployment:
            This label is set to the name of the deployment.

        cmk/container_name:
            This label is set to the name of the container

        cmk/container_image:
            This label is set to the image of the container.

    """

    if not section:
        return

    yield HostLabel("cmk/kubernetes/object", "deployment")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    yield HostLabel("cmk/kubernetes/namespace", section.namespace)
    yield HostLabel("cmk/kubernetes/deployment", section.name)

    for container in section.containers:
        yield HostLabel("cmk/container_name", container)

    for image in section.images:
        yield HostLabel("cmk/container_image", image)


register.agent_section(
    name="kube_deployment_info_v1",
    parsed_section_name="kube_deployment_info",
    parse_function=parse,
    host_label_function=host_labels,
)


def discovery(section: DeploymentInfo) -> DiscoveryResult:
    yield Service()


def check_kube_deployment_info(section: DeploymentInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "namespace": section.namespace,
            "creation_timestamp": section.creation_timestamp,
        }
    )


register.check_plugin(
    name="kube_deployment_info",
    service_name="Info",
    discovery_function=discovery,
    check_function=check_kube_deployment_info,
)
