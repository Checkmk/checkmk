#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Mapping, NoReturn, Sequence, Tuple
from unittest.mock import MagicMock

import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes import performance
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.transform_any import parse_labels

from .factory import (
    api_to_agent_cluster,
    api_to_agent_daemonset,
    api_to_agent_node,
    api_to_agent_statefulset,
    APIDaemonSetFactory,
    APINodeFactory,
    APIPodFactory,
    APIStatefulSetFactory,
    ClusterDetailsFactory,
    ContainerSpecFactory,
    MetaDataFactory,
    node_status,
    NodeMetaDataFactory,
    NodeResourcesFactory,
    PodSpecFactory,
    PodStatusFactory,
)


class PerformanceMetricFactory(ModelFactory):
    __model__ = performance.PerformanceMetric


def cluster_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_count_v1",
        "kube_cluster_details_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_cluster_info_v1",
        "kube_collector_daemons_v1",
    ]


def _cluster_builder_from_agents(
    *,
    cluster_details: api.ClusterDetails | None = None,
    excluded_node_roles: Sequence[str] = (),
    daemonsets: Sequence[agent.DaemonSet] = (),
    statefulsets: Sequence[agent.StatefulSet] = (),
    deployments: Sequence[agent.Deployment] = (),
    pods: Sequence[api.Pod] = (),
    nodes: Sequence[agent.Node] = (),
    cluster_aggregation_pods: Sequence[api.Pod] = (),
    cluster_aggregation_nodes: Sequence[api.Node] = (),
) -> agent.Cluster:
    return agent.Cluster(
        cluster_details=cluster_details or ClusterDetailsFactory.build(),
        excluded_node_roles=excluded_node_roles,
        nodes=nodes,
        statefulsets=statefulsets,
        deployments=deployments,
        daemonsets=daemonsets,
        pods=pods,
        cluster_aggregation_nodes=cluster_aggregation_nodes,
        cluster_aggregation_pods=cluster_aggregation_pods,
    )


def test_cluster_namespaces() -> None:
    pod_metadata = MetaDataFactory.build()
    pod = APIPodFactory.build(metadata=pod_metadata)
    cluster = _cluster_builder_from_agents(pods=[pod])
    assert cluster.namespaces() == {pod_metadata.namespace}


@pytest.mark.parametrize("cluster_pods", [0, 10, 20])
def test_cluster_resources(cluster_pods: int) -> None:
    pod_containers_count = 2
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                node=None, containers=ContainerSpecFactory.batch(pod_containers_count)
            )
        )
        for _ in range(cluster_pods)
    ]
    cluster = _cluster_builder_from_agents(pods=pods, cluster_aggregation_pods=pods)
    assert cluster.memory_resources().count_total == cluster_pods * pod_containers_count
    assert cluster.cpu_resources().count_total == cluster_pods * pod_containers_count
    assert sum(len(pods) for _phase, pods in cluster.pod_resources()) == cluster_pods


def test_cluster_allocatable_memory_resource() -> None:
    memory = 2.0 * 1024
    resources = {
        "capacity": NodeResourcesFactory.build(),
        "allocatable": NodeResourcesFactory.build(memory=memory),
    }
    api_nodes = APINodeFactory.batch(size=3, resources=resources)
    agent_nodes = [api_to_agent_node(api_node) for api_node in api_nodes]
    cluster = _cluster_builder_from_agents(nodes=agent_nodes, cluster_aggregation_nodes=api_nodes)

    expected = section.AllocatableResource(context="cluster", value=memory * 3)
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


def test_cluster_allocatable_cpu_resource():
    cpu = 2.0
    number_nodes = 3
    resources = {
        "capacity": NodeResourcesFactory.build(),
        "allocatable": NodeResourcesFactory.build(cpu=cpu),
    }
    api_nodes = APINodeFactory.batch(size=number_nodes, resources=resources)
    agent_nodes = [api_to_agent_node(api_node) for api_node in api_nodes]
    cluster = _cluster_builder_from_agents(nodes=agent_nodes, cluster_aggregation_nodes=api_nodes)

    expected = section.AllocatableResource(context="cluster", value=cpu * number_nodes)
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    cluster = _cluster_builder_from_agents()
    agent.write_cluster_api_sections("cluster", cluster)
    assert list(write_sections_mock.call_args[0][0]) == cluster_api_sections()


def test_write_cluster_api_sections_maps_section_names_to_callables(
    write_sections_mock: MagicMock,
) -> None:
    cluster = _cluster_builder_from_agents()
    agent.write_cluster_api_sections("cluster", cluster)
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in cluster_api_sections()
    )


@pytest.mark.parametrize("cluster_nodes", [0, 10, 20])
def test_node_count_returns_number_of_nodes_ready_not_ready(cluster_nodes: int) -> None:
    nodes = [
        api_to_agent_node(node)
        for node in APINodeFactory.batch(
            size=cluster_nodes, status=node_status(api.NodeConditionStatus.TRUE)
        )
    ]
    cluster = _cluster_builder_from_agents(nodes=nodes)
    node_count = cluster.node_count()
    assert node_count.worker.ready + node_count.worker.not_ready == cluster_nodes


def test_node_control_plane_count() -> None:
    api_node = api_to_agent_node(
        APINodeFactory.build(
            roles=["master"],
            status=node_status(api.NodeConditionStatus.TRUE),
        )
    )
    cluster = _cluster_builder_from_agents(nodes=[api_node])
    node_count = cluster.node_count()
    assert node_count.worker.total == 0
    assert node_count.control_plane.total == 1
    assert node_count.control_plane.ready == 1


def test_node_control_plane_not_ready_count() -> None:
    api_node = api_to_agent_node(
        APINodeFactory.build(
            roles=["master"],
            status=node_status(api.NodeConditionStatus.FALSE),
        )
    )
    cluster = _cluster_builder_from_agents(nodes=[api_node])
    node_count = cluster.node_count()
    assert node_count.control_plane.not_ready == 1


@pytest.mark.parametrize("cluster_daemon_sets", [0, 10, 20])
def test_daemon_sets_returns_daemon_sets_of_cluster(cluster_daemon_sets: int) -> None:
    daemonsets = [
        api_to_agent_daemonset(d) for d in APIDaemonSetFactory.batch(size=cluster_daemon_sets)
    ]
    cluster = _cluster_builder_from_agents(daemonsets=daemonsets)
    daemon_sets = cluster.daemonsets
    assert len(daemon_sets) == cluster_daemon_sets


@pytest.mark.parametrize("cluster_statefulsets", [0, 10, 20])
def test_statefulsets_returns_statefulsets_of_cluster(cluster_statefulsets: int) -> None:
    agent_statefulsets = [
        api_to_agent_statefulset(s) for s in APIStatefulSetFactory.batch(size=cluster_statefulsets)
    ]
    cluster = _cluster_builder_from_agents(statefulsets=agent_statefulsets)
    statefulsets = cluster.statefulsets
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
    memory = 7.0 * 1024**3
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=memory * counted_nodes)
    cluster = api_to_agent_cluster(
        excluded_node_roles=excluded_node_roles,
        nodes=[
            APINodeFactory.build(
                resources={"allocatable": NodeResourcesFactory.build(memory=memory)},
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
def test_create_correct_number_pod_names_for_cluster_host(
    phase_all_pods: api.Phase,
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
) -> None:
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

    def _raise_error() -> NoReturn:
        raise ValueError()

    cluster_pods = agent.determine_pods_to_host(
        monitored_objects=[],
        monitored_pods=set(),
        cluster=cluster,
        monitored_namespaces=set(),
        api_pods=pods,
        resource_quotas=[],
        monitored_api_namespaces=[],
        api_cron_jobs=[],
        # This test is not supposed to generate any PiggyBack host:
        piggyback_formatter=_raise_error,  # type: ignore[arg-type]
        piggyback_formatter_node=_raise_error,  # type: ignore[arg-type]
    ).cluster_pods

    total = (
        sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
        if phase_all_pods == api.Phase.RUNNING
        else 0
    )

    assert len(cluster_pods) == total


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
