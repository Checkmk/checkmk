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
from cmk.base.plugins.agent_based.utils.kube import kube_labels_to_cmk_labels, NamespaceInfo
from cmk.base.plugins.agent_based.utils.kube_info import check_info


def parse_kube_namespace_info(string_table: StringTable):
    """Parses `string_table` into a NodeInfo instance

    >>> parse_kube_namespace_info([['{"architecture": "amd64",'
    ... '"name": "namespace",'
    ... '"creation_timestamp": "1640000000.0",'
    ... '"cluster": "cluster",'
    ... '"labels": {}}'
    ... ]])
    NamespaceInfo(name='namespace', creation_timestamp=1640000000.0, labels={}, cluster='cluster')
    """
    return NamespaceInfo(**json.loads(string_table[0][0]))


def host_labels(section: NamespaceInfo) -> HostLabelGenerator:
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

    """
    yield HostLabel("cmk/kubernetes", "yes")
    yield HostLabel("cmk/kubernetes/object", "namespace")
    yield HostLabel("cmk/kubernetes/cluster", section.cluster)
    yield HostLabel("cmk/kubernetes/namespace", section.name)
    yield from kube_labels_to_cmk_labels(section.labels)


register.agent_section(
    name="kube_namespace_info_v1",
    parsed_section_name="kube_namespace_info",
    parse_function=parse_kube_namespace_info,
    host_label_function=host_labels,
)


def discovery_kube_namespace_info(section: NamespaceInfo) -> DiscoveryResult:
    yield Service()


def check_kube_namespace_info(section: NamespaceInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "creation_timestamp": section.creation_timestamp,
        }
    )


register.check_plugin(
    name="kube_namespace_info",
    service_name="Info",
    discovery_function=discovery_kube_namespace_info,
    check_function=check_kube_namespace_info,
)
