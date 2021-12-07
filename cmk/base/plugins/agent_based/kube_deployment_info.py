#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    HostLabel,
    register,
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
from cmk.base.plugins.agent_based.utils.k8s import DeploymentInfo


def parse(string_table: StringTable) -> DeploymentInfo:
    """Parses `string_table` into a DeploymentInfo instance"""
    return DeploymentInfo(**json.loads(string_table[0][0]))


def host_labels(section: DeploymentInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
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


def check(section: DeploymentInfo) -> CheckResult:
    # TODO: complete check implementation
    yield Result(state=State.OK, summary=f"Name: {section.name}")


register.check_plugin(
    name="kube_deployment_info",
    service_name="Info",
    discovery_function=discovery,
    check_function=check,
)
