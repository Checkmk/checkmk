#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.kube.agent_handlers.common
from cmk.plugins.kube.agent_handlers.common import aggregate_resources
from cmk.plugins.kube.api_server import SUPPORTED_VERSIONS
from cmk.plugins.kube.schemata import api, section
from cmk.plugins.kube.special_agents import agent_kube as agent

from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    APICronJobFactory,
    APIDeploymentFactory,
    APINodeFactory,
    APIPodFactory,
    composed_entities_builder,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    MetaDataFactory,
    pod_phase_generator,
    PodSpecFactory,
    PodStatusFactory,
)


class ResourcesRequirementsFactory(ModelFactory):
    __model__ = api.ResourcesRequirements


def test_pod_node_allocation_within_cluster() -> None:
    """Test pod is correctly allocated to node within cluster"""
    node = APINodeFactory.build()
    pod = APIPodFactory.build(spec=PodSpecFactory.build(node=node.metadata.name))
    cluster = composed_entities_builder(pods=[pod], nodes=[node])
    assert len(cluster.nodes) == 1
    assert len(cluster.nodes[0].pods) == 1


def test_pod_deployment_allocation_within_cluster() -> None:
    """Test pod is correctly allocated to deployment within cluster"""
    cluster = composed_entities_builder(deployments=[APIDeploymentFactory.build()])
    assert len(cluster.deployments) == 1
    assert len(cluster.deployments[0].pods) == 1


ONE_KiB = 1024
ONE_MiB = 1024 * ONE_KiB


def container_spec(
    request_cpu: float | None = 1.0,
    limit_cpu: float | None = 2.0,
    request_memory: float | None = 1.0 * ONE_MiB,
    limit_memory: float | None = 2.0 * ONE_MiB,
) -> api.ContainerSpec:
    return ContainerSpecFactory.build(
        resources=api.ContainerResources(
            limits=api.ResourcesRequirements(memory=limit_memory, cpu=limit_cpu),
            requests=api.ResourcesRequirements(memory=request_memory, cpu=request_cpu),
        )
    )


def test_aggregate_resources_summed_request_cpu() -> None:
    container_specs = [container_spec(request_cpu=request) for request in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.request == 2.0
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_request_memory() -> None:
    container_specs = [
        container_spec(request_memory=request) for request in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", container_specs)
    assert result.request == 2.0 * ONE_MiB
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_limit_cpu() -> None:
    container_specs = [container_spec(limit_cpu=limit) for limit in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.limit == 2.0
    assert result.count_unspecified_limits == 1


def test_aggregate_resources_summed_limit_memory() -> None:
    container_specs = [
        container_spec(limit_memory=limit) for limit in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", container_specs)
    assert result.limit == 2.0 * ONE_MiB


def test_aggregate_resources_with_only_zeroed_limit_cpu() -> None:
    container_specs = [container_spec(limit_cpu=limit) for limit in [0.0, 0.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.count_zeroed_limits == 2


def test_aggregate_resources_with_only_zeroed_limit_memory() -> None:
    container_specs = [container_spec(limit_memory=limit) for limit in [0.0, 0.0]]
    result = aggregate_resources("memory", container_specs)
    assert result.count_zeroed_limits == 2


@pytest.mark.parametrize("pods_count", [0, 5])
def test_pod_resources_from_api_pods(pods_count: int) -> None:
    pods = [
        APIPodFactory.build(
            metadata=MetaDataFactory.build(name=str(i), factory_use_construct=True),
            status=PodStatusFactory.build(
                phase=api.Phase.RUNNING,
            ),
        )
        for i in range(pods_count)
    ]

    pod_resources = cmk.plugins.kube.agent_handlers.common.pod_resources_from_api_pods(pods)

    assert pod_resources == section.PodResources(
        running=[str(i) for i in range(pods_count)],
    )


def test_pod_name() -> None:
    name = "name"
    namespace = "namespace"
    pod = APIPodFactory.build(
        metadata=MetaDataFactory.build(name=name, namespace=namespace, factory_use_construct=True)
    )

    pod_name = cmk.plugins.kube.agent_handlers.common.pod_name(pod)
    pod_namespaced_name = cmk.plugins.kube.agent_handlers.common.pod_name(
        pod, prepend_namespace=True
    )

    assert pod_name == name
    assert pod_namespaced_name == f"{namespace}_{name}"


def test_filter_pods_by_namespace() -> None:
    pod_one = APIPodFactory.build(
        metadata=MetaDataFactory.build(name="pod_one", namespace="one", factory_use_construct=True)
    )
    pod_two = APIPodFactory.build(
        metadata=MetaDataFactory.build(name="pod_two", namespace="two", factory_use_construct=True)
    )

    filtered_pods = agent.filter_pods_by_namespace([pod_one, pod_two], api.NamespaceName("one"))

    assert [pod.metadata.name for pod in filtered_pods] == ["pod_one"]


def test_filter_pods_by_cron_job() -> None:
    pod_one = APIPodFactory.build(
        uid="in_cron_job",
    )
    pod_two = APIPodFactory.build(
        uid="not_in_cron_job",
    )
    cron_job = APICronJobFactory.build(
        pod_uids=[
            "in_cron_job",
        ]
    )
    filtered_pods = agent.filter_pods_by_cron_job([pod_one, pod_two], cron_job)
    assert [pod.uid for pod in filtered_pods] == ["in_cron_job"]


@pytest.mark.parametrize(
    "phase",
    [
        api.Phase.PENDING,
        api.Phase.RUNNING,
        api.Phase.FAILED,
        api.Phase.SUCCEEDED,
        api.Phase.UNKNOWN,
    ],
)
def test_filter_pods_by_phase(phase: api.Phase) -> None:
    pods_count = len(api.Phase)
    phases = pod_phase_generator()
    pods = [
        APIPodFactory.build(status=PodStatusFactory.build(phase=next(phases)))
        for _ in range(pods_count)
    ]

    pods_in_phase = agent.filter_pods_by_phase(pods, phase)

    assert [pod.status.phase for pod in pods_in_phase] == [phase]


@pytest.mark.parametrize("pods_count", [0, 5])
def test_collect_workload_resources_from_api_pods(pods_count: int) -> None:
    requirements = ResourcesRequirementsFactory.build(memory=ONE_MiB, cpu=0.5)
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                containers=[
                    ContainerSpecFactory.build(
                        resources=ContainerResourcesFactory.build(
                            limits=requirements, requests=requirements
                        )
                    )
                ]
            )
        )
        for _ in range(pods_count)
    ]

    memory_resources = (
        cmk.plugins.kube.agent_handlers.common.collect_memory_resources_from_api_pods(pods)
    )
    cpu_resources = cmk.plugins.kube.agent_handlers.common.collect_cpu_resources_from_api_pods(pods)

    assert memory_resources == section.Resources(
        request=pods_count * ONE_MiB,
        limit=pods_count * ONE_MiB,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 0.5,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )


@pytest.mark.parametrize("pods_count", [5, 10, 15])
def test_collect_workload_resources_from_agent_pods(pods_count: int) -> None:
    requests = ResourcesRequirementsFactory.build(memory=ONE_MiB, cpu=0.5)
    limits = ResourcesRequirementsFactory.build(memory=2 * ONE_MiB, cpu=1.0)
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                containers=[
                    ContainerSpecFactory.build(
                        resources=ContainerResourcesFactory.build(limits=limits, requests=requests)
                    )
                ]
            )
        )
        for _ in range(pods_count)
    ]

    memory_resources = (
        cmk.plugins.kube.agent_handlers.common.collect_memory_resources_from_api_pods(pods)
    )
    cpu_resources = cmk.plugins.kube.agent_handlers.common.collect_cpu_resources_from_api_pods(pods)

    assert memory_resources == section.Resources(
        request=pods_count * ONE_MiB,
        limit=pods_count * ONE_MiB * 2,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 1.0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )


def test_collect_workload_resources_from_agent_pods_no_pods_in_cluster() -> None:
    memory_resources = (
        cmk.plugins.kube.agent_handlers.common.collect_memory_resources_from_api_pods([])
    )
    cpu_resources = cmk.plugins.kube.agent_handlers.common.collect_cpu_resources_from_api_pods([])
    empty_section = section.Resources(
        request=0.0,
        limit=0.0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=0,
    )

    assert memory_resources == empty_section
    assert cpu_resources == empty_section


def test_version_verification_and_docstring_do_not_diverge():
    """Keep _verify_version and arg_parser help text in sync.

    Make sure to update the agent_kube.__doc__, since it is used by the arg_parser. Only
    version_string is important, but we give a bit more context in order to ensure it is not
    included for the wrong reason.

    Note, that the __doc__ only mentions the supported versions. `LOWEST_FUNCTIONING_VERSION`
    does not affect this text, since we only increment it, if a issue becomes known.
    """

    lowest_supported_version = min(SUPPORTED_VERSIONS)
    version_string = f"v{lowest_supported_version[0]}.{lowest_supported_version[1]}"
    assert f"agent requires Kubernetes version {version_string} or higher" in agent.__doc__.replace(
        "\n", " "
    )
