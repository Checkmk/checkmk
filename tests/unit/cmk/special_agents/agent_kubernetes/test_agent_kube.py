#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_deployment,
    api_to_agent_pod,
    APIDeploymentFactory,
    APIPodFactory,
    MetaDataFactory,
    PodMetaDataFactory,
)

from cmk.special_agents.agent_kube import (
    _collect_cpu_resources,
    kube_objects_from_namespaces,
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
        metadata = api.PodMetaData(name="", namespace="default", labels={})
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
    # Arrange
    pods = [
        api_to_agent_pod(
            APIPodFactory.build(
                metadata=PodMetaDataFactory.build(
                    name="one", namespace=api.NamespaceName("default")
                ),
            )
        ),
        api_to_agent_pod(
            APIPodFactory.build(
                metadata=PodMetaDataFactory.build(
                    name="two", namespace=api.NamespaceName("standard")
                )
            )
        ),
    ]

    # Act
    filtered_pods = pods_from_namespaces(pods, {api.NamespaceName("default")})

    # Assert
    assert len(filtered_pods) == 1
    assert filtered_pods[0].name() == "one"


def test_filter_deployments_from_monitored_namespaces():
    # Arrange
    deployments = [
        api_to_agent_deployment(
            APIDeploymentFactory.build(
                metadata=MetaDataFactory.build(namespace=api.NamespaceName("default"))
            ),
        ),
        api_to_agent_deployment(
            APIDeploymentFactory.build(
                metadata=MetaDataFactory.build(namespace=api.NamespaceName("standard"))
            ),
        ),
    ]

    # Act
    filtered_deployments = kube_objects_from_namespaces(deployments, {api.NamespaceName("default")})

    # Assert
    assert [deployment.namespace for deployment in filtered_deployments] == ["default"]
