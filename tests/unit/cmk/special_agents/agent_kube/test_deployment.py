#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence
from unittest.mock import MagicMock, Mock

from pydantic_factories import ModelFactory

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_deployment,
    api_to_agent_pod,
    APIDeploymentFactory,
    APIPodFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


class DeploymentConditionFactory(ModelFactory):
    __model__ = api.DeploymentCondition


def test_pod_deployment_controller_name(pod: agent.Pod) -> None:
    pod._controllers.append(section.Controller(type_=section.ControllerType.deployment, name="hi"))
    pod_info = pod.info("cluster", "host", agent.AnnotationNonPatternOption.ignore_all)
    assert len(pod_info.controllers) == 1
    assert pod_info.controllers[0].name == "hi"


def test_deployment_pod_resources_one_pod_per_phase() -> None:
    # Assemble
    deployment = api_to_agent_deployment(APIDeploymentFactory.build())
    for phase in api.Phase:
        pod = api_to_agent_pod(APIPodFactory.build(status=PodStatusFactory.build(phase=phase)))
        deployment.add_pod(pod)

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


def test_deployment_memory_resources(
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_memory: float,
    container_request_memory: float,
) -> None:
    deployment = api_to_agent_deployment(APIDeploymentFactory.build())
    deployment.add_pod(new_pod())
    memory_resources = deployment.memory_resources()
    assert memory_resources.count_total == pod_containers_count
    assert memory_resources.limit == pod_containers_count * container_limit_memory
    assert memory_resources.request == pod_containers_count * container_request_memory


def test_deployment_cpu_resources(
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_cpu: float,
    container_request_cpu: float,
) -> None:
    deployment = api_to_agent_deployment(APIDeploymentFactory.build())
    deployment.add_pod(new_pod())
    cpu_resources = deployment.cpu_resources()
    assert cpu_resources.count_total == pod_containers_count
    assert cpu_resources.limit == pod_containers_count * container_limit_cpu
    assert cpu_resources.request == pod_containers_count * container_request_cpu


def test_write_deployments_api_sections_registers_sections_to_be_written(
    deployments_api_sections: Sequence[str],
    write_sections_mock: MagicMock,
) -> None:
    deployment = api_to_agent_deployment(APIDeploymentFactory.build())
    deployment.add_pod(api_to_agent_pod(APIPodFactory.build()))
    agent.write_deployments_api_sections(
        "cluster", agent.AnnotationNonPatternOption.ignore_all, [deployment], "host", Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == deployments_api_sections
