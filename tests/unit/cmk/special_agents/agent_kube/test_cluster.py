#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
from contextlib import redirect_stdout
from typing import Callable, Iterable, Mapping, Sequence, Tuple

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.utils import kube_resources

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.transform_any import parse_labels

from .conftest import (
    api_to_agent_cluster,
    APINodeFactory,
    APIPodFactory,
    NodeMetaDataFactory,
    NodeResourcesFactory,
    ONE_GiB,
    PodSpecFactory,
    PodStatusFactory,
)
from .factory import api_to_agent_daemonset, APIDaemonSetFactory, MetaDataFactory


class PerformanceMetricFactory(ModelFactory):
    __model__ = agent.PerformanceMetric


class RateMetricFactory(ModelFactory):
    __model__ = agent.RateMetric


class PerformanceContainerFactory(ModelFactory):
    __model__ = agent.PerformanceContainer


def test_cluster_namespaces(
    cluster_details: api.ClusterDetails, pod_metadata: api.PodMetaData
) -> None:
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    api_pod = APIPodFactory.build(metadata=pod_metadata)
    cluster.add_pod(
        agent.Pod(
            api_pod.uid,
            api_pod.metadata,
            api_pod.status,
            api_pod.spec,
            api_pod.containers,
            api_pod.init_containers,
        )
    )
    assert cluster.namespaces() == {pod_metadata.namespace}


@pytest.mark.parametrize("cluster_pods", [0, 10, 20])
def test_cluster_resources(  # type:ignore[no-untyped-def]
    cluster_details: api.ClusterDetails,
    cluster_pods: int,
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
):
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    for _ in range(cluster_pods):
        cluster.add_pod(new_pod())
    assert cluster.memory_resources().count_total == cluster_pods * pod_containers_count
    assert cluster.cpu_resources().count_total == cluster_pods * pod_containers_count
    assert sum(len(pods) for _phase, pods in cluster.pod_resources()) == cluster_pods


def test_cluster_allocatable_memory_resource(  # type:ignore[no-untyped-def]
    node_allocatable_memory: float, cluster_nodes: int, cluster: agent.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_memory * cluster_nodes
    )
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


def test_cluster_allocatable_cpu_resource(  # type:ignore[no-untyped-def]
    node_allocatable_cpu: float, cluster_nodes: int, cluster: agent.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_cpu * cluster_nodes
    )
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written(  # type:ignore[no-untyped-def]
    cluster: agent.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent.write_cluster_api_sections("cluster", cluster)
    assert list(write_sections_mock.call_args[0][0]) == cluster_api_sections


def test_write_cluster_api_sections_maps_section_names_to_callables(  # type:ignore[no-untyped-def]
    cluster: agent.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent.write_cluster_api_sections("cluster", cluster)
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in cluster_api_sections
    )


@pytest.mark.parametrize("cluster_nodes", [0, 10, 20])
def test_node_count_returns_number_of_nodes_ready_not_ready(  # type:ignore[no-untyped-def]
    cluster_nodes: int, cluster: agent.Cluster
):
    node_count = cluster.node_count()
    assert node_count.worker.ready + node_count.worker.not_ready == cluster_nodes


@pytest.mark.parametrize("node_is_control_plane", [True])
def test_node_control_plane_count(cluster_details: api.ClusterDetails, node: agent.Node) -> None:
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    cluster.add_node(node)
    node_count = cluster.node_count()
    assert node_count.worker.total == 0
    assert node_count.control_plane.total == 1
    assert node_count.control_plane.ready == 1


@pytest.mark.parametrize("node_is_control_plane", [True])
@pytest.mark.parametrize("node_condition_status", [api.ConditionStatus.FALSE])
def test_node_control_plane_not_ready_count(
    cluster_details: api.ClusterDetails, node: agent.Node
) -> None:
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    cluster.add_node(node)
    node_count = cluster.node_count()
    assert node_count.control_plane.not_ready == 1


@pytest.mark.parametrize("cluster_daemon_sets", [0, 10, 20])
def test_daemon_sets_returns_daemon_sets_of_cluster(  # type:ignore[no-untyped-def]
    cluster_daemon_sets: int, cluster: agent.Cluster
):
    daemon_sets = cluster.daemon_sets()
    assert len(daemon_sets) == cluster_daemon_sets


@pytest.mark.parametrize("cluster_statefulsets", [0, 10, 20])
def test_statefulsets_returns_statefulsets_of_cluster(  # type:ignore[no-untyped-def]
    cluster_statefulsets, cluster
) -> None:
    statefulsets = cluster.statefulsets()
    assert len(statefulsets) == cluster_statefulsets


# Tests for exclusion via node role


@pytest.mark.parametrize("excluded_node_roles", [["control-plane"], [], ["master"]])
@pytest.mark.parametrize(
    "api_node_roles_per_node, cluster_nodes, expected_control_nodes",
    [
        (
            [["control-piano"], ["gold"], ["silver"]],
            3,
            0,
        ),
        (
            [["control-plane"], ["gold"], ["control-plane"]],
            3,
            2,
        ),
        (
            [["control-plane, blue"], ["vegis", "control-plane, fish"], ["control-plane"]],
            3,
            3,
        ),
    ],
)
def test_cluster_allocatable_memory_resource_exclude_roles(  # type:ignore[no-untyped-def]
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
):
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=7.0 * ONE_GiB * counted_nodes)
    cluster = api_to_agent_cluster(
        excluded_node_roles=excluded_node_roles,
        nodes=[
            APINodeFactory.build(
                resources={"allocatable": NodeResourcesFactory.build(memory=7.0 * ONE_GiB)},
                roles=roles,
            )
            for roles in api_node_roles_per_node
        ],
    )
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


@pytest.mark.parametrize("excluded_node_roles", [["control-plane"], [], ["master"]])
@pytest.mark.parametrize(
    "api_node_roles_per_node, cluster_nodes, expected_control_nodes",
    [
        (
            [["control-piano"], ["gold"], ["silver"]],
            3,
            0,
        ),
        (
            [["control-plane"], ["gold"], ["control-plane"]],
            3,
            2,
        ),
        (
            [["control-plane, blue"], ["vegis", "control-plane, fish"], ["control-plane"]],
            3,
            3,
        ),
    ],
)
def test_cluster_allocatable_cpu_resource_cluster(  # type:ignore[no-untyped-def]
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
):
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=6.0 * counted_nodes)
    cluster = api_to_agent_cluster(
        excluded_node_roles=excluded_node_roles,
        nodes=[
            APINodeFactory.build(
                resources={"allocatable": NodeResourcesFactory.build(cpu=6.0)},
                roles=roles,
            )
            for roles in api_node_roles_per_node
        ],
    )
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_cluster_usage_resources(  # type:ignore[no-untyped-def]
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    total = sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(count, spec=PodSpecFactory.build(node=node))
    ]
    nodes = [
        APINodeFactory.build(metadata=NodeMetaDataFactory.build(name=node), roles=roles)
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    assert cluster.memory_resources().count_total == len(APIPodFactory.build().containers) * total
    assert cluster.cpu_resources().count_total == len(APIPodFactory.build().containers) * total
    assert sum(len(pods) for _, pods in cluster.pod_resources()) == total


@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_cluster_allocatable_pods(  # type:ignore[no-untyped-def]
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    allocatable = 110
    capacity = 111  # can not be different in pratice, but better for testing
    total = sum(1 for *_, roles in node_podcount_roles if excluded_node_role not in roles)
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(count, spec=PodSpecFactory.build(node=node))
    ]
    nodes = [
        APINodeFactory.build(
            metadata=NodeMetaDataFactory.build(name=node),
            resources={
                "allocatable": NodeResourcesFactory.build(pods=allocatable),
                "capacity": NodeResourcesFactory.build(pods=capacity),
            },
            roles=roles,
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    assert cluster.allocatable_pods().capacity == total * capacity
    assert cluster.allocatable_pods().allocatable == total * allocatable


@pytest.mark.parametrize("phase_all_pods", list(api.Phase))
@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_write_kube_object_performance_section_cluster(  # type:ignore[no-untyped-def]
    phase_all_pods: api.Phase,
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    # Initialize API data
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(
            count,
            spec=PodSpecFactory.build(node=node),
            status=PodStatusFactory.build(phase=phase_all_pods),
        )
    ]
    nodes = [
        APINodeFactory.build(
            metadata=NodeMetaDataFactory.build(name=node),
            roles=roles,
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    # Initialize cluster collector data
    container_count = 3  # this count may differ from the one used to generate API data
    performance_pods = {
        agent.pod_lookup_from_api_pod(pod): agent.PerformancePod(
            lookup_name=agent.pod_lookup_from_api_pod(pod),
            containers=PerformanceContainerFactory.batch(
                container_count,
                metrics={
                    "memory_working_set_bytes": PerformanceMetricFactory.build(value=1.0 * ONE_GiB),
                },
                rate_metrics={"cpu_usage_seconds_total": RateMetricFactory.build(rate=1.0)},
            ),
        )
        for pod in pods
    }

    # Write Cluster performance sections to output by capturing stdout
    with io.StringIO() as buf, redirect_stdout(buf):
        agent.write_kube_object_performance_section_cluster(cluster, performance_pods)
        output = buf.getvalue().splitlines()

    # Check correctness
    total = (
        sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
        if phase_all_pods == api.Phase.RUNNING
        else 0
    )
    if total == 0:
        # If there are no running pods on non-filtered nodes, no sections should be produced
        assert "<<<kube_performance_cpu_v1:sep(0)>>>" not in output
        assert "<<<kube_performance_memory_v1:sep(0)>>>" not in output
    else:
        for current_row, next_row in zip(output[:-1], output[1:]):
            if current_row == "<<<kube_performance_cpu_v1:sep(0)>>>":
                cpu_section = kube_resources.parse_performance_usage([[next_row]])
            elif current_row == "<<<kube_performance_memory_v1:sep(0)>>>":
                memory_section = kube_resources.parse_performance_usage([[next_row]])
        assert cpu_section.resource.usage == total * container_count * 1.0
        assert memory_section.resource.usage == total * container_count * 1.0 * ONE_GiB


@pytest.mark.parametrize(
    "labels_per_daemonset, expected_error",
    [
        pytest.param(
            [
                {"random-label": "machine-sections"},
                {"node-collector": "machine-sections"},
                {"node-collector": "container-metrics"},
            ],
            section.IdentificationError(
                duplicate_machine_collector=False,
                duplicate_container_collector=False,
                unknown_collector=False,
            ),
            id="No errors.",
        ),
        pytest.param(
            [
                {"node-collector": ""},
                {"node-collector": "machine-sections"},
                {"node-collector": "container-metrics"},
            ],
            section.IdentificationError(
                duplicate_machine_collector=False,
                duplicate_container_collector=False,
                unknown_collector=True,
            ),
            id="Unknown collector (empty label value).",
        ),
        pytest.param(
            [
                {"node-collector": "machine-sections"},
                {"node-collector": "machine-sections"},
            ],
            section.IdentificationError(
                duplicate_machine_collector=True,
                duplicate_container_collector=False,
                unknown_collector=False,
            ),
            id="Duplicate DaemonSet with machine-sections label.",
        ),
        pytest.param(
            [
                {"node-collector": "container-metrics"},
                {"node-collector": "container-metrics"},
            ],
            section.IdentificationError(
                duplicate_machine_collector=False,
                duplicate_container_collector=True,
                unknown_collector=False,
            ),
            id="Duplicate DaemonSet with container-metrics label.",
        ),
        pytest.param(
            [
                {"node-collector": "some-stuff"},
                {"node-collector": "container-metrics"},
                {"node-collector": "container-metrics"},
                {"node-collector": "machine-sections"},
                {"node-collector": "machine-sections"},
            ],
            section.IdentificationError(
                duplicate_machine_collector=True,
                duplicate_container_collector=True,
                unknown_collector=True,
            ),
            id="All possible errors.",
        ),
    ],
)
def test__node_collector_daemons_error_handling(
    labels_per_daemonset: Iterable[Mapping[str, str] | None],
    expected_error: section.IdentificationError,
) -> None:
    daemonsets = [
        api_to_agent_daemonset(
            APIDaemonSetFactory.build(
                metadata=MetaDataFactory.build(labels=parse_labels(labels)),
            )
        )
        for labels in labels_per_daemonset
    ]
    collector_daemons = agent._node_collector_daemons(daemonsets)

    assert collector_daemons.errors == expected_error
    if expected_error.duplicate_container_collector:
        assert collector_daemons.container is None
    if expected_error.duplicate_machine_collector:
        assert collector_daemons.machine is None


DAEMONSET_MACHINE_SECTIONS = api_to_agent_daemonset(
    APIDaemonSetFactory.build(
        metadata=MetaDataFactory.build(
            labels=parse_labels({"node-collector": "machine-sections"}),
        ),
    )
)
DAEMONSET_CONTAINER_METRICS = api_to_agent_daemonset(
    APIDaemonSetFactory.build(
        metadata=MetaDataFactory.build(
            labels=parse_labels({"node-collector": "container-metrics"})
        ),
    )
)
DAEMONSET_NOT_A_COLLECTOR = api_to_agent_daemonset(
    APIDaemonSetFactory.build(
        metadata=MetaDataFactory.build(
            labels=parse_labels({"random-label": "container-metrics"}),
        ),
    )
)


@pytest.mark.parametrize(
    "daemonsets",
    [
        pytest.param(
            [DAEMONSET_NOT_A_COLLECTOR, DAEMONSET_MACHINE_SECTIONS, DAEMONSET_CONTAINER_METRICS],
            id="container-metrics node collector in last position.",
        ),
        pytest.param(
            [DAEMONSET_CONTAINER_METRICS, DAEMONSET_MACHINE_SECTIONS, DAEMONSET_NOT_A_COLLECTOR],
            id="container-metrics node collector in first position.",
        ),
    ],
)
def test__node_collector_daemons_identify_container_collector(
    daemonsets: Iterable[agent.DaemonSet],
) -> None:
    collector_daemons = agent._node_collector_daemons(daemonsets)

    assert collector_daemons.errors == section.IdentificationError(
        duplicate_machine_collector=False,
        duplicate_container_collector=False,
        unknown_collector=False,
    )
    assert collector_daemons.container is not None
    assert (
        DAEMONSET_CONTAINER_METRICS._status.number_available
        == collector_daemons.container.available
    )
    assert (
        DAEMONSET_CONTAINER_METRICS._status.desired_number_scheduled
        == collector_daemons.container.desired
    )


@pytest.mark.parametrize(
    "daemonsets",
    [
        pytest.param(
            [DAEMONSET_NOT_A_COLLECTOR, DAEMONSET_CONTAINER_METRICS, DAEMONSET_MACHINE_SECTIONS],
            id="machine-metrics node collector in last position.",
        ),
        pytest.param(
            [DAEMONSET_MACHINE_SECTIONS, DAEMONSET_NOT_A_COLLECTOR, DAEMONSET_CONTAINER_METRICS],
            id="machine-metrics node collector in first position.",
        ),
    ],
)
def test__node_collector_daemons_identify_machine_collector(
    daemonsets: Iterable[agent.DaemonSet],
) -> None:
    collector_daemons = agent._node_collector_daemons(daemonsets)

    assert collector_daemons.errors == section.IdentificationError(
        duplicate_machine_collector=False,
        duplicate_container_collector=False,
        unknown_collector=False,
    )
    assert collector_daemons.machine is not None
    assert (
        DAEMONSET_MACHINE_SECTIONS._status.number_available == collector_daemons.machine.available
    )
    assert (
        DAEMONSET_MACHINE_SECTIONS._status.desired_number_scheduled
        == collector_daemons.machine.desired
    )


@pytest.mark.parametrize(
    "daemonsets",
    [
        pytest.param(
            [DAEMONSET_NOT_A_COLLECTOR, DAEMONSET_MACHINE_SECTIONS],
            id="The is no container-metrics node collector, but the"
            "machine-sections collector is present.",
        ),
    ],
)
def test__node_collector_daemons_missing_container_collector(
    daemonsets: Sequence[agent.DaemonSet],
) -> None:
    collector_daemons = agent._node_collector_daemons(daemonsets)

    assert not collector_daemons.errors.duplicate_container_collector
    assert collector_daemons.container is None


@pytest.mark.parametrize(
    "daemonsets",
    [
        pytest.param(
            [DAEMONSET_CONTAINER_METRICS, DAEMONSET_NOT_A_COLLECTOR],
            id="There is no machine-sections node collector, but the "
            "container-metrics collector is present.",
        ),
    ],
)
def test__node_collector_daemons_missing_machine_collector(
    daemonsets: Sequence[agent.DaemonSet],
) -> None:
    collector_daemons = agent._node_collector_daemons(daemonsets)

    assert not collector_daemons.errors.duplicate_machine_collector
    assert collector_daemons.machine is None


def test__node_collector_daemons_no_daemonsets() -> None:
    collector_daemons = agent._node_collector_daemons([])

    assert not collector_daemons.errors.duplicate_machine_collector
    assert collector_daemons.machine is None
    assert collector_daemons.container is None
