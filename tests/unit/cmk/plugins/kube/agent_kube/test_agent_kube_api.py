#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name


import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    APICronJobFactory,
    APIDeploymentFactory,
    APINodeFactory,
    APIPodFactory,
    composed_entities_builder,
    ContainerSpecFactory,
    MetaDataFactory,
    pod_phase_generator,
    PodSpecFactory,
    PodStatusFactory,
    ResourceRequirementsFactory,
)

import cmk.plugins.kube.agent_handlers.common
from cmk.plugins.kube.agent_handlers.common import aggregate_resources
from cmk.plugins.kube.api_server import SUPPORTED_VERSIONS
from cmk.plugins.kube.schemata import api, section
from cmk.plugins.kube.special_agents import agent_kube as agent


class ResourceRequirementFactory(ModelFactory):
    __model__ = api.ResourceRequirement


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

_UNSET_RESOURCES = api.ResourceRequirements(
    limits=api.ResourceRequirement(),
    requests=api.ResourceRequirement(),
)


def container_spec(
    request_cpu: float | None = 1.0,
    limit_cpu: float | None = 2.0,
    request_memory: float | None = 1.0 * ONE_MiB,
    limit_memory: float | None = 2.0 * ONE_MiB,
) -> api.ContainerSpec:
    return ContainerSpecFactory.build(
        resources=api.ResourceRequirements(
            limits=api.ResourceRequirement(memory=limit_memory, cpu=limit_cpu),
            requests=api.ResourceRequirement(memory=request_memory, cpu=request_cpu),
        )
    )


def _pod_with_container(spec: api.ContainerSpec) -> api.Pod:
    return APIPodFactory.build(
        spec=PodSpecFactory.build(containers=[spec], resources=_UNSET_RESOURCES)
    )


def test_aggregate_resources_summed_request_cpu() -> None:
    pods = [_pod_with_container(container_spec(request_cpu=r)) for r in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", pods)
    assert result.request == 2.0
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_request_memory() -> None:
    pods = [
        _pod_with_container(container_spec(request_memory=r))
        for r in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", pods)
    assert result.request == 2.0 * ONE_MiB
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_limit_cpu() -> None:
    pods = [_pod_with_container(container_spec(limit_cpu=l)) for l in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", pods)
    assert result.limit == 2.0
    assert result.count_unspecified_limits == 1


def test_aggregate_resources_summed_limit_memory() -> None:
    pods = [
        _pod_with_container(container_spec(limit_memory=l))
        for l in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", pods)
    assert result.limit == 2.0 * ONE_MiB


def test_aggregate_resources_with_only_zeroed_limit_cpu() -> None:
    pods = [_pod_with_container(container_spec(limit_cpu=l)) for l in [0.0, 0.0]]
    result = aggregate_resources("cpu", pods)
    assert result.count_zeroed_limits == 2


def test_aggregate_resources_with_only_zeroed_limit_memory() -> None:
    pods = [_pod_with_container(container_spec(limit_memory=l)) for l in [0.0, 0.0]]
    result = aggregate_resources("memory", pods)
    assert result.count_zeroed_limits == 2


@pytest.mark.parametrize(
    "pod_cpu_resources,expected_request,expected_limit,expected_pod_level_request,expected_pod_level_limit,expected_total_requests,expected_total_limits",
    [
        pytest.param(
            api.ResourceRequirements(
                requests=api.ResourceRequirement(cpu=3.0),
                limits=api.ResourceRequirement(),
            ),
            3.0,
            2.0,
            1,
            0,
            0,
            1,
            id="pod-level request, container limit",
        ),
        pytest.param(
            api.ResourceRequirements(
                requests=api.ResourceRequirement(),
                limits=api.ResourceRequirement(cpu=5.0),
            ),
            1.0,
            5.0,
            0,
            1,
            1,
            0,
            id="container request, pod-level limit",
        ),
        pytest.param(
            api.ResourceRequirements(
                requests=api.ResourceRequirement(cpu=3.0),
                limits=api.ResourceRequirement(cpu=5.0),
            ),
            3.0,
            5.0,
            1,
            1,
            0,
            0,
            id="both pod-level",
        ),
        pytest.param(
            api.ResourceRequirements(
                requests=api.ResourceRequirement(cpu=0.0),
                limits=api.ResourceRequirement(cpu=0.0),
            ),
            1.0,
            2.0,
            0,
            0,
            1,
            1,
            id="when pod-level are 0, use container-level",
        ),
    ],
)
def test_aggregate_resources_pod_level_cpu(
    pod_cpu_resources: api.ResourceRequirements,
    expected_request: float,
    expected_limit: float,
    expected_pod_level_request: int,
    expected_pod_level_limit: int,
    expected_total_requests: int,
    expected_total_limits: int,
) -> None:
    pod = APIPodFactory.build(
        spec=PodSpecFactory.build(
            containers=[container_spec(request_cpu=1.0, limit_cpu=2.0)],
            resources=pod_cpu_resources,
        )
    )
    result = aggregate_resources("cpu", [pod])
    assert result.request == expected_request
    assert result.limit == expected_limit
    assert result.count_pods_pod_level_request == expected_pod_level_request
    assert result.count_pods_pod_level_limit == expected_pod_level_limit
    assert result.count_total_requests == expected_total_requests
    assert result.count_total_limits == expected_total_limits


def test_aggregate_resources_mixed_pod_and_container_level_cpu() -> None:
    pod_level = APIPodFactory.build(
        spec=PodSpecFactory.build(
            containers=[container_spec(request_cpu=1.0, limit_cpu=2.0)],
            resources=api.ResourceRequirements(
                requests=api.ResourceRequirement(cpu=3.0),
                limits=api.ResourceRequirement(cpu=5.0),
            ),
        )
    )
    container_level = _pod_with_container(container_spec(request_cpu=1.0, limit_cpu=2.0))
    result = aggregate_resources("cpu", [pod_level, container_level])
    assert result.request == 4.0  # 3.0 pod-level + 1.0 container
    assert result.limit == 7.0  # 5.0 pod-level + 2.0 container
    assert result.count_pods_pod_level_request == 1
    assert result.count_pods_pod_level_limit == 1
    assert result.count_total_requests == 1
    assert result.count_total_limits == 1


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
    requirements = ResourceRequirementFactory.build(memory=ONE_MiB, cpu=0.5)
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                containers=[
                    ContainerSpecFactory.build(
                        resources=ResourceRequirementsFactory.build(
                            limits=requirements, requests=requirements
                        )
                    )
                ],
                resources=_UNSET_RESOURCES,
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
        count_total_requests=pods_count,
        count_total_limits=pods_count,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 0.5,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total_requests=pods_count,
        count_total_limits=pods_count,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
    )


@pytest.mark.parametrize("pods_count", [5, 10, 15])
def test_collect_workload_resources_from_agent_pods(pods_count: int) -> None:
    requests = ResourceRequirementFactory.build(memory=ONE_MiB, cpu=0.5)
    limits = ResourceRequirementFactory.build(memory=2 * ONE_MiB, cpu=1.0)
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                containers=[
                    ContainerSpecFactory.build(
                        resources=ResourceRequirementsFactory.build(
                            limits=limits, requests=requests
                        )
                    )
                ],
                resources=_UNSET_RESOURCES,
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
        count_total_requests=pods_count,
        count_total_limits=pods_count,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 1.0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total_requests=pods_count,
        count_total_limits=pods_count,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
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
        count_total_requests=0,
        count_total_limits=0,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
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
