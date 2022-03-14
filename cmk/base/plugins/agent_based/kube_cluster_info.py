#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
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
from cmk.base.plugins.agent_based.utils.kube import ClusterInfo


def parse_kube_cluster_info(string_table: StringTable) -> ClusterInfo:
    """
    >>> parse_kube_cluster_info([[
    ... '{"name": "cluster"}'
    ... ]])
    ClusterInfo(name='cluster')
    """
    return ClusterInfo(**json.loads(string_table[0][0]))


def host_labels(section: ClusterInfo) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/kubernetes/object:
            This label is set to the Kubernetes object type.

        cmk/kubernetes/cluster:
            This label is set to the given Kubernetes cluster name.
    """
    yield HostLabel("cmk/kubernetes/object", "cluster")
    yield HostLabel("cmk/kubernetes/cluster", section.name)


register.agent_section(
    name="kube_cluster_info_v1",
    parsed_section_name="kube_cluster_info",
    parse_function=parse_kube_cluster_info,
    host_label_function=host_labels,
)


def discovery_kube_cluster_info(section: ClusterInfo) -> DiscoveryResult:
    yield Service()


def check_kube_cluster_info(section: ClusterInfo) -> CheckResult:
    yield Result(state=State.OK, summary=f"Name: {section.name}")


register.check_plugin(
    name="kube_cluster_info",
    service_name="Info",
    discovery_function=discovery_kube_cluster_info,
    check_function=check_kube_cluster_info,
)
