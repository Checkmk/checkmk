#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence
from unittest.mock import MagicMock, Mock

from pydantic_factories import ModelFactory

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_deployment,
    APIControllerFactory,
    APIDeploymentFactory,
    APIPodFactory,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api


class DeploymentConditionFactory(ModelFactory):
    __model__ = api.DeploymentCondition


def deployments_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_deployment_info_v1",
        "kube_deployment_conditions_v1",
        "kube_cpu_resources_v1",
        "kube_update_strategy_v1",
        "kube_deployment_replicas_v1",
    ]


def test_pod_deployment_controller_name() -> None:
    pod = APIPodFactory.build(controllers=[APIControllerFactory.build(name="hi", namespace="bye")])
    pod_info = agent.pod_info(pod, "cluster", "host", agent.AnnotationNonPatternOption.ignore_all)
    assert len(pod_info.controllers) == 1
    assert pod_info.controllers[0].name == "hi"


def test_deployment_pod_resources_one_pod_per_phase() -> None:
    # Assemble
    deployment = APIDeploymentFactory.build()
    deployment = api_to_agent_deployment(
        APIDeploymentFactory.build(),
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )

    # Act
    pod_resources = deployment.pod_resources()

    # Assert
    for _phase, pods in pod_resources:
        assert len(pods) == 1


def test_deployment_conditions() -> None:
    api_deployment = APIDeploymentFactory.build()
    deployment_conditions = ["available", "progressing", "replicafailure"]
    api_deployment.status.conditions = {
        condition: DeploymentConditionFactory.build() for condition in deployment_conditions
    }
    deployment = api_to_agent_deployment(api_deployment)
    conditions = deployment.conditions()
    assert conditions is not None
    assert all(condition_details is not None for _, condition_details in conditions)


def test_deployment_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    deployment = api_to_agent_deployment(APIDeploymentFactory.build(), pods=[api_pod])
    memory_resources = deployment.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_deployment_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    deployment = api_to_agent_deployment(APIDeploymentFactory.build(), pods=[api_pod])
    cpu_resources = deployment.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


def test_write_deployments_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    deployment = api_to_agent_deployment(APIDeploymentFactory.build(), pods=[APIPodFactory.build()])
    agent.write_deployments_api_sections(
        "cluster", agent.AnnotationNonPatternOption.ignore_all, [deployment], "host", Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == deployments_api_sections()
