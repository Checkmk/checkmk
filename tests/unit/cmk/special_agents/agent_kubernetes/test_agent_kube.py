#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.special_agents.agent_kube import (
    _collect_cpu_resources,
    aggregate_resources,
    Pod,
    pods_from_namespaces,
)
from cmk.special_agents.utils_kubernetes.schemata import api


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
        spec=api.PodSpec(restart_policy="Always", containers=[], init_containers=[])
        if "spec" not in attributes
        else attributes["spec"],
        containers={} if "containers" not in attributes else attributes["containers"],
        init_containers={}
        if "init_containers" not in attributes
        else attributes["init_containers"],
    )


# TODO: see CMK-9525
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
                        image_pull_policy="Always",
                        resources=api.ContainerResources(
                            limits=api.ResourcesRequirements(
                                cpu=0.4,
                            ),
                            requests=api.ResourcesRequirements(),
                        ),
                    )
                ],
                init_containers=[],
            )
        },
    )
    assert _collect_cpu_resources([pod]).request == 0.0
    assert _collect_cpu_resources([pod]).limit == 0.4


def test_filter_pods_from_namespaces():
    pod_one = default_pod(
        "one", metadata=api.PodMetaData(name="one", namespace=api.Namespace("default"))
    )
    pod_two = default_pod(
        "two", metadata=api.PodMetaData(name="two", namespace=api.Namespace("standard"))
    )
    assert pods_from_namespaces([pod_one, pod_two], {api.Namespace("default")}) == [pod_one]


def test_aggregate_resources_summed_request() -> None:
    request_values = [None, 1.0, 1.0]
    result = aggregate_resources(request_values, len(request_values) * [None])
    assert result.request == 2.0
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_limit() -> None:
    limit_values = [None, 1.0, 1.0, 0.0, 0.0]
    result = aggregate_resources(len(limit_values) * [None], limit_values)
    assert result.limit == 2.0
    assert result.count_unspecified_limits == 1


def test_aggregate_resources_with_only_zeroed_limits() -> None:
    limit_values = [0.0, 0.0]
    result = aggregate_resources(len(limit_values) * [None], limit_values)
    assert result.count_zeroed_limits == 2
