#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.special_agents.agent_kube import _collect_cpu_resources, Pod, pods_from_namespaces
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.schemata.section import ExceptionalResource


def default_pod(
    uid: str,
    metadata: Optional[api.PodMetaData] = None,
    attributes: Optional[Mapping[str, Any]] = None,
) -> Pod:
    if metadata is None:
        metadata = api.PodMetaData(name="", namespace="default")
    if attributes is None:
        attributes = {}
    return Pod(
        uid=api.PodUID(uid),
        metadata=metadata,
        status=api.PodStatus(
            conditions=[],
            phase=api.Phase.RUNNING,
            start_time=None,
            qos_class="burstable",
        )
        if "status" not in attributes
        else attributes["status"],
        spec=api.PodSpec(restart_policy="Always", containers=[])
        if "spec" not in attributes
        else attributes["spec"],
        containers={} if "containers" not in attributes else attributes["containers"],
    )


def test_collect_cpu_resources():
    """Test the _collect_cpu_resources aggregation function"""
    pod = default_pod(
        "POD",
        attributes={
            "spec": api.PodSpec(
                restart_policy="Always",
                containers=[
                    api.ContainerSpec(
                        name="container",
                        resources=api.ContainerResources(
                            limits=api.ResourcesRequirements(
                                cpu=0.4,
                            ),
                            requests=api.ResourcesRequirements(),
                        ),
                    )
                ],
            )
        },
    )
    assert _collect_cpu_resources([pod]) == section.Resources(
        request=ExceptionalResource.unspecified,
        limit=0.4,
    )


def test_filter_pods_from_namespaces():
    pod_one = default_pod(
        "one", metadata=api.PodMetaData(name="one", namespace=api.Namespace("default"))
    )
    pod_two = default_pod(
        "two", metadata=api.PodMetaData(name="two", namespace=api.Namespace("standard"))
    )
    assert pods_from_namespaces([pod_one, pod_two], {api.Namespace("default")}) == [pod_one]
