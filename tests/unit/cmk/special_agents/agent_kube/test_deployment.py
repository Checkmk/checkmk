#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence
from unittest.mock import MagicMock, Mock

import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api


class DeploymentConditionFactory(ModelFactory):
    __model__ = api.DeploymentCondition


def test_pod_deployment_controller_name(pod: agent.Pod, deployment: agent.Deployment) -> None:
    pod.add_controller(deployment)
    pod_info = pod.info("cluster", agent.AnnotationNonPatternOption.ignore_all)
    assert len(pod_info.controllers) == 1
    assert pod_info.controllers[0].name == deployment.name()


@pytest.mark.parametrize("deployment_pods", [0, 10, 20])
def test_deployment_pod_resources_returns_all_pods(
    deployment: agent.Deployment, deployment_pods: int
):
    pod_resources = deployment.pod_resources()
    assert sum(len(pods) for _, pods in pod_resources) == deployment_pods


def test_deployment_pod_resources_one_pod_per_phase(deployment: agent.Deployment) -> None:
    for _phase, pods in deployment.pod_resources():
        assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_deployment_pod_resources_pods_in_phase(
    deployment: agent.Deployment, deployment_pods: int
) -> None:
    assert len(deployment.pods()) == deployment_pods


def test_deployment_conditions(
    api_deployment: api.Deployment,
):
    deployment_conditions = ["available", "progressing", "replicafailure"]
    api_deployment.status.conditions = {
        condition: DeploymentConditionFactory.build() for condition in deployment_conditions
    }
    deployment = agent.Deployment(
        api_deployment.metadata, api_deployment.spec, api_deployment.status
    )
    conditions = deployment.conditions()
    assert conditions is not None
    assert all(condition_details is not None for _, condition_details in conditions)


def test_deployment_memory_resources(
    new_deployment: Callable[[], agent.Deployment],
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_memory: float,
    container_request_memory: float,
):
    deployment = new_deployment()
    deployment.add_pod(new_pod())
    memory_resources = deployment.memory_resources()
    assert memory_resources.count_total == pod_containers_count
    assert memory_resources.limit == pod_containers_count * container_limit_memory
    assert memory_resources.request == pod_containers_count * container_request_memory


def test_deployment_cpu_resources(
    new_deployment: Callable[[], agent.Deployment],
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_cpu: float,
    container_request_cpu: float,
):
    deployment = new_deployment()
    deployment.add_pod(new_pod())
    cpu_resources = deployment.cpu_resources()
    assert cpu_resources.count_total == pod_containers_count
    assert cpu_resources.limit == pod_containers_count * container_limit_cpu
    assert cpu_resources.request == pod_containers_count * container_request_cpu


def test_write_deployments_api_sections_registers_sections_to_be_written(
    deployment: agent.Deployment,
    deployments_api_sections: Sequence[str],
    write_sections_mock: MagicMock,
):
    agent.write_deployments_api_sections(
        "cluster", agent.AnnotationNonPatternOption.ignore_all, [deployment], Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == deployments_api_sections
