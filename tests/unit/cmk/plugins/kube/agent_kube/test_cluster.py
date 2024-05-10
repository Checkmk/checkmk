#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import NoReturn

import pytest

from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    APIDaemonSetFactory,
    APIDataFactory,
    APINodeFactory,
    APIPodFactory,
    APIStatefulSetFactory,
    composed_entities_builder,
    ContainerSpecFactory,
    MetaDataFactory,
    NodeMetaDataFactory,
    NodeResourcesFactory,
    NodeStatusFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.plugins.kube.agent_handlers.cluster_handler import (
    _allocatable_cpu_resource,
    _allocatable_memory_resource,
    _allocatable_pods,
    _cpu_resources,
    _memory_resources,
    _node_collector_daemons,
    _node_count,
    _node_is_ready,
    _pod_resources,
    create_api_sections,
)
from cmk.plugins.kube.agent_handlers.common import Cluster
from cmk.plugins.kube.schemata import api, section
from cmk.plugins.kube.special_agents import agent_kube as agent


def _create_labels_from_roles(roles: Sequence[str]) -> dict[str, str]:
    return {f"node-role.kubernetes.io/{role}": "" for role in roles}


def cluster_api_sections() -> set[str]:
    return {
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
    }


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
    cluster = Cluster.from_api_resources((), APIDataFactory.build(pods=pods))
    assert _memory_resources(cluster).count_total == cluster_pods * pod_containers_count
    assert _cpu_resources(cluster).count_total == cluster_pods * pod_containers_count
    assert sum(len(pods) for _phase, pods in _pod_resources(cluster)) == cluster_pods


def test_cluster_allocatable_memory_resource() -> None:
    memory = 2.0 * 1024
    number_nodes = 3
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(memory=memory, factory_use_construct=True)
    )
    nodes = APINodeFactory.batch(size=number_nodes, status=status)
    cluster = Cluster.from_api_resources((), APIDataFactory.build(nodes=nodes))

    expected = section.AllocatableResource(context="cluster", value=memory * number_nodes)
    actual = _allocatable_memory_resource(cluster)
    assert actual == expected


def test_cluster_allocatable_cpu_resource():
    cpu = 2.0
    number_nodes = 3
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(cpu=cpu, factory_use_construct=True)
    )
    nodes = APINodeFactory.batch(size=number_nodes, status=status)
    cluster = Cluster.from_api_resources((), APIDataFactory.build(nodes=nodes))

    expected = section.AllocatableResource(context="cluster", value=cpu * number_nodes)
    actual = _allocatable_cpu_resource(cluster)
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written() -> None:
    cluster = Cluster.from_api_resources((), APIDataFactory.build())
    sections = create_api_sections(cluster, "cluster")
    assert {s.section_name for s in sections} == cluster_api_sections()


@pytest.mark.parametrize("cluster_node_count", [0, 10, 20])
def test_node_count(cluster_node_count: int) -> None:
    nodes = APINodeFactory.batch(size=cluster_node_count)
    cluster = Cluster.from_api_resources((), APIDataFactory.build(nodes=nodes))
    section_node_count = _node_count(cluster)
    assert len(section_node_count.nodes) == cluster_node_count


def test__node_is_ready_with_ready_node() -> None:
    status = NodeStatusFactory.build(
        conditions=[api.NodeCondition(type_="Ready", status=api.NodeConditionStatus.TRUE)]
    )
    api_node = APINodeFactory.build(status=status)
    assert _node_is_ready(api_node) is True


def test__node_is_ready_with_unready_node() -> None:
    status = NodeStatusFactory.build(
        conditions=[api.NodeCondition(type_="Ready", status=api.NodeConditionStatus.FALSE)]
    )
    api_node = APINodeFactory.build(status=status)
    assert _node_is_ready(api_node) is False


@pytest.mark.parametrize("cluster_daemon_sets", [0, 10, 20])
def test_daemon_sets_returns_daemon_sets_of_cluster(cluster_daemon_sets: int) -> None:
    composed_entities = composed_entities_builder(
        daemonsets=APIDaemonSetFactory.batch(size=cluster_daemon_sets)
    )
    assert len(composed_entities.daemonsets) == cluster_daemon_sets


@pytest.mark.parametrize("cluster_statefulsets", [0, 10, 20])
def test_statefulsets_returns_statefulsets_of_cluster(cluster_statefulsets: int) -> None:
    composed_entities = composed_entities_builder(
        statefulsets=APIStatefulSetFactory.batch(size=cluster_statefulsets)
    )
    assert len(composed_entities.statefulsets) == cluster_statefulsets


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
def test_cluster_allocatable_memory_resource_exclude_roles(
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
) -> None:
    memory = 7.0 * 1024**3
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=memory * counted_nodes)
    cluster = Cluster.from_api_resources(
        excluded_node_roles=excluded_node_roles,
        api_data=APIDataFactory.build(
            nodes=[
                APINodeFactory.build(
                    metadata=NodeMetaDataFactory.build(
                        labels=_create_labels_from_roles(roles), factory_use_construct=True
                    ),
                    status=NodeStatusFactory.build(
                        allocatable=NodeResourcesFactory.build(
                            memory=memory, factory_use_construct=True
                        )
                    ),
                )
                for roles in api_node_roles_per_node
            ],
        ),
    )
    actual = _allocatable_memory_resource(cluster)
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
def test_cluster_allocatable_cpu_resource_cluster(
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
) -> None:
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=6.0 * counted_nodes)
    cluster = Cluster.from_api_resources(
        excluded_node_roles=excluded_node_roles,
        api_data=APIDataFactory.build(
            nodes=[
                APINodeFactory.build(
                    metadata=NodeMetaDataFactory.build(
                        labels=_create_labels_from_roles(roles), factory_use_construct=True
                    ),
                    status=NodeStatusFactory.build(
                        allocatable=NodeResourcesFactory.build(cpu=6.0, factory_use_construct=True)
                    ),
                )
                for roles in api_node_roles_per_node
            ],
        ),
    )
    actual = _allocatable_cpu_resource(cluster)
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
def test_cluster_usage_resources(
    excluded_node_role: str,
    node_podcount_roles: Sequence[tuple[str, int, Sequence[str]]],
) -> None:
    total = sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(count, spec=PodSpecFactory.build(node=node))
    ]
    nodes = [
        APINodeFactory.build(
            metadata=NodeMetaDataFactory.build(
                name=node, labels=_create_labels_from_roles(roles), factory_use_construct=True
            )
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = Cluster.from_api_resources(
        [excluded_node_role],
        APIDataFactory.build(pods=pods, nodes=nodes),
    )

    assert _memory_resources(cluster).count_total == len(APIPodFactory.build().containers) * total
    assert _cpu_resources(cluster).count_total == len(APIPodFactory.build().containers) * total
    assert sum(len(pods) for _, pods in _pod_resources(cluster)) == total


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
def test_cluster_allocatable_pods(
    excluded_node_role: str,
    node_podcount_roles: Sequence[tuple[str, int, Sequence[str]]],
) -> None:
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
            metadata=NodeMetaDataFactory.build(
                name=node, labels=_create_labels_from_roles(roles), factory_use_construct=True
            ),
            status=NodeStatusFactory.build(
                allocatable=NodeResourcesFactory.build(
                    pods=allocatable, factory_use_construct=True
                ),
                capacity=NodeResourcesFactory.build(pods=capacity, factory_use_construct=True),
            ),
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = Cluster.from_api_resources(
        [excluded_node_role],
        APIDataFactory.build(pods=pods, nodes=nodes),
    )

    assert _allocatable_pods(cluster).capacity == total * capacity
    assert _allocatable_pods(cluster).allocatable == total * allocatable


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
    node_podcount_roles: Sequence[tuple[str, int, Sequence[str]]],
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
            metadata=NodeMetaDataFactory.build(
                name=node, labels=_create_labels_from_roles(roles), factory_use_construct=True
            ),
        )
        for node, _, roles in node_podcount_roles
    ]
    composed_entities = agent.ComposedEntities.from_api_resources(
        excluded_node_roles=[excluded_node_role],
        api_data=APIDataFactory.build(
            pods=pods,
            nodes=nodes,
            deployments=(),
            statefulsets=(),
            daemonsets=(),
        ),
    )

    def _raise_error() -> NoReturn:
        raise ValueError()

    pods_to_host = agent.determine_pods_to_host(
        monitored_objects=[],
        composed_entities=composed_entities,
        monitored_namespaces=set(),
        api_pods=pods,
        resource_quotas=[],
        monitored_api_namespaces=[],
        api_cron_jobs=[],
        # This test is not supposed to generate any PiggyBack host:
        piggyback_formatter=_raise_error,  # type: ignore[arg-type]
    )
    cluster_piggy_back = [p for p in pods_to_host.piggybacks if p.piggyback == ""]

    total = (
        sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
        if phase_all_pods == api.Phase.RUNNING
        else 0
    )

    assert len(cluster_piggy_back) == 1
    assert len(cluster_piggy_back[0].pod_names) == total


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
        APIDaemonSetFactory.build(
            metadata=MetaDataFactory.build(
                labels=api.parse_labels(labels), factory_use_construct=True
            ),
        )
        for labels in labels_per_daemonset
    ]
    collector_daemons = _node_collector_daemons(daemonsets)

    assert collector_daemons.errors == expected_error
    if expected_error.duplicate_container_collector:
        assert collector_daemons.container is None
    if expected_error.duplicate_machine_collector:
        assert collector_daemons.machine is None


DAEMONSET_MACHINE_SECTIONS = APIDaemonSetFactory.build(
    metadata=MetaDataFactory.build(
        labels=api.parse_labels({"node-collector": "machine-sections"}),
        factory_use_construct=True,
    ),
)
DAEMONSET_CONTAINER_METRICS = APIDaemonSetFactory.build(
    metadata=MetaDataFactory.build(
        labels=api.parse_labels({"node-collector": "container-metrics"}),
        factory_use_construct=True,
    ),
)
DAEMONSET_NOT_A_COLLECTOR = APIDaemonSetFactory.build(
    metadata=MetaDataFactory.build(
        labels=api.parse_labels({"random-label": "container-metrics"}),
        factory_use_construct=True,
    ),
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
    daemonsets: Iterable[api.DaemonSet],
) -> None:
    collector_daemons = _node_collector_daemons(daemonsets)

    assert collector_daemons.errors == section.IdentificationError(
        duplicate_machine_collector=False,
        duplicate_container_collector=False,
        unknown_collector=False,
    )
    assert collector_daemons.container is not None
    assert (
        DAEMONSET_CONTAINER_METRICS.status.number_available == collector_daemons.container.available
    )
    assert (
        DAEMONSET_CONTAINER_METRICS.status.desired_number_scheduled
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
    daemonsets: Iterable[api.DaemonSet],
) -> None:
    collector_daemons = _node_collector_daemons(daemonsets)

    assert collector_daemons.errors == section.IdentificationError(
        duplicate_machine_collector=False,
        duplicate_container_collector=False,
        unknown_collector=False,
    )
    assert collector_daemons.machine is not None
    assert DAEMONSET_MACHINE_SECTIONS.status.number_available == collector_daemons.machine.available
    assert (
        DAEMONSET_MACHINE_SECTIONS.status.desired_number_scheduled
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
    daemonsets: Sequence[api.DaemonSet],
) -> None:
    collector_daemons = _node_collector_daemons(daemonsets)

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
    daemonsets: Sequence[api.DaemonSet],
) -> None:
    collector_daemons = _node_collector_daemons(daemonsets)

    assert not collector_daemons.errors.duplicate_machine_collector
    assert collector_daemons.machine is None


def test__node_collector_daemons_no_daemonsets() -> None:
    collector_daemons = _node_collector_daemons([])

    assert not collector_daemons.errors.duplicate_machine_collector
    assert collector_daemons.machine is None
    assert collector_daemons.container is None
