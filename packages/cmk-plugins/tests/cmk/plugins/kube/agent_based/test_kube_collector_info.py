#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"
# ruff: noqa: SLF001  # Private member accessed


import json
from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, LevelsT, Metric, Result, State
from cmk.plugins.kube.agent_based import kube_collector_info
from cmk.plugins.kube.schemata.section import (
    CacheHealth,
    CacheSizeInfo,
    CheckmkKubeAgentMetadata,
    ClusterCollectorMetadata,
    CollectorComponentsMetadata,
    CollectorDaemons,
    CollectorHandlerLog,
    CollectorProcessingLogs,
    CollectorState,
    CollectorType,
    HostName,
    IdentificationError,
    NodeCollectorReplica,
    NodeComponent,
    NodeMetadata,
    NodeName,
    OsName,
    PlatformMetadata,
    PythonCompiler,
    Version,
)


class ClusterCollectorMetadataFactory(ModelFactory):
    __model__ = ClusterCollectorMetadata


class NodeMetadataFactory(ModelFactory):
    __model__ = NodeMetadata


class CollectorDaemonsFactory(ModelFactory):
    __model__ = CollectorDaemons

    # Allows better reasoning about the test cases, where this Model is of no
    # importance. Sadly, this field cannot be set in the build method.
    __allow_none_optionals__ = False


class CollectorHandlerLogFactory(ModelFactory):
    __model__ = CollectorHandlerLog


@pytest.fixture
def raw_collector_metadata() -> Mapping[str, object]:
    return {
        "processing_log": {"status": "ok", "title": "title", "detail": "detail"},
        "cluster_collector": {
            "node": "node",
            "host_name": "host",
            "container_platform": {
                "os_name": "os",
                "os_version": "version",
                "python_version": "pversion",
                "python_compiler": "compiler",
            },
            "checkmk_kube_agent": {"project_version": "package"},
            "cache_health": {
                "container_metrics": {
                    "size": 259,
                    "maxsize": 50000,
                },
                "machine_sections": {
                    "size": 2,
                    "maxsize": 10000,
                },
            },
        },
        "nodes": [
            {
                "name": "minikube",
                "components": {
                    "checkmk_agent_version": {
                        "collector_type": "Machine Sections",
                        "checkmk_kube_agent": {"project_version": "0.1.0"},
                        "name": "checkmk_agent_version",
                        "version": "version",
                    },
                },
            }
        ],
    }


def test_parse_collector_metadata(raw_collector_metadata: Mapping[str, object]) -> None:
    string_table_element = json.dumps(raw_collector_metadata)
    assert kube_collector_info.parse_collector_metadata(
        [[string_table_element]]
    ) == CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK, title="title", detail="detail"
        ),
        cluster_collector=ClusterCollectorMetadata(
            node=NodeName("node"),
            host_name=HostName("host"),
            container_platform=PlatformMetadata(
                os_name=OsName("os"),
                os_version=Version("version"),
                python_version=Version("pversion"),
                python_compiler=PythonCompiler("compiler"),
            ),
            checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version=Version("package")),
            cache_health=CacheHealth(
                container_metrics=CacheSizeInfo(size=259, maxsize=50000),
                machine_sections=CacheSizeInfo(size=2, maxsize=10000),
            ),
        ),
        nodes=[
            NodeMetadata(
                name=NodeName("minikube"),
                components={
                    "checkmk_agent_version": NodeComponent(
                        collector_type=CollectorType.MACHINE_SECTIONS,
                        checkmk_kube_agent=CheckmkKubeAgentMetadata(
                            project_version=Version("0.1.0")
                        ),
                        name="checkmk_agent_version",
                        version=Version("version"),
                    ),
                },
            )
        ],
    )


def test_parse_collector_metadata_without_cache_stats(
    raw_collector_metadata: Mapping[str, object],
) -> None:
    cluster_collector = raw_collector_metadata["cluster_collector"]
    assert isinstance(cluster_collector, dict)
    del cluster_collector["cache_health"]
    string_table_element = json.dumps(raw_collector_metadata)
    assert kube_collector_info.parse_collector_metadata(
        [[string_table_element]]
    ) == CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK, title="title", detail="detail"
        ),
        cluster_collector=ClusterCollectorMetadata(
            node=NodeName("node"),
            host_name=HostName("host"),
            container_platform=PlatformMetadata(
                os_name=OsName("os"),
                os_version=Version("version"),
                python_version=Version("pversion"),
                python_compiler=PythonCompiler("compiler"),
            ),
            checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version=Version("package")),
            cache_health=None,
        ),
        nodes=[
            NodeMetadata(
                name=NodeName("minikube"),
                components={
                    "checkmk_agent_version": NodeComponent(
                        collector_type=CollectorType.MACHINE_SECTIONS,
                        checkmk_kube_agent=CheckmkKubeAgentMetadata(
                            project_version=Version("0.1.0")
                        ),
                        name="checkmk_agent_version",
                        version=Version("version"),
                    ),
                },
            )
        ],
    )


def test_parse_collector_components() -> None:
    string_table_element = json.dumps(
        {
            "container": {"status": "ok", "title": "title", "detail": "detail"},
            "machine": {"status": "ok", "title": "title", "detail": "detail"},
        }
    )
    assert kube_collector_info.parse_collector_processing_logs(
        [[string_table_element]]
    ) == CollectorProcessingLogs(
        container=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
        machine=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
    )


def test_cache_result_zero_maxsize() -> None:
    cache = CacheSizeInfo(size=100, maxsize=0)
    result = kube_collector_info._cache_result(
        cache,
        "Test cache",
        ("fixed", (80.0, 95.0)),
        wants_percentage=True,
    )
    assert result == Result(
        state=State.UNKNOWN,
        summary="Test cache: Cache max size is 0, this is likely a configuration error",
    )


def test_parse_collector_daemons() -> None:
    string_table_element = json.dumps(
        {
            "container": {"available": 3, "desired": 3},
            "machine": {"available": 2, "desired": 3},
            "errors": {
                "duplicate_machine_collector": False,
                "duplicate_container_collector": False,
                "unknown_collector": False,
            },
        }
    )
    assert kube_collector_info.parse_collector_daemons(
        [[string_table_element]]
    ) == CollectorDaemons(
        container=NodeCollectorReplica(available=3, desired=3),
        machine=NodeCollectorReplica(available=2, desired=3),
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        ),
    )


def test_check_all_ok_sections() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            cache_health=None,
        ),
        nodes=NodeMetadataFactory.batch(1),
    )
    collector_processing_logs = CollectorProcessingLogs(
        container=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="OK"),
        machine=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="OK"),
    )
    collector_daemons = CollectorDaemonsFactory.build(
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        )
    )

    # Act
    check_result = list(
        kube_collector_info.check(
            kube_collector_info.DEFAULT_PARAMS,
            collector_metadata,
            collector_processing_logs,
            collector_daemons,
        )
    )

    # Assert
    assert len(check_result) == 6
    assert all(isinstance(result, Result) for result in check_result)
    assert all(result.state == State.OK for result in check_result if isinstance(result, Result))


def test_check_with_no_collector_components_section() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            cache_health=None,
        ),
        nodes=NodeMetadataFactory.batch(1),
    )
    collector_daemons = CollectorDaemonsFactory.build(
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        )
    )

    # Act
    check_result = list(
        kube_collector_info.check(
            kube_collector_info.DEFAULT_PARAMS,
            collector_metadata,
            None,
            collector_daemons,
        )
    )

    # Assert
    assert all(isinstance(result, Result) for result in check_result)
    assert isinstance(check_result[0], Result) and check_result[0].summary.startswith(
        "Cluster collector version:"
    )
    assert len(check_result) == 4


def test_check_with_no_machine_component_with_params() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLogFactory.build(status=CollectorState.OK),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            cache_health=CacheHealth(
                container_metrics=CacheSizeInfo(size=150, maxsize=10000),
                machine_sections=CacheSizeInfo(size=4, maxsize=400),
            ),
        ),
        nodes=NodeMetadataFactory.batch(1),
    )
    collector_processing_logs = CollectorProcessingLogs(
        container=CollectorHandlerLogFactory.build(status=CollectorState.OK),
        machine=CollectorHandlerLog(status=CollectorState.ERROR, title="title", detail="OK"),
    )
    collector_daemons = CollectorDaemonsFactory.build(
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        )
    )

    # Act
    check_result = list(
        kube_collector_info.check(
            {**kube_collector_info.DEFAULT_PARAMS, "machine_metrics": 0},
            collector_metadata,
            collector_processing_logs,
            collector_daemons,
        )
    )

    # Assert
    assert [
        r.state
        for r in check_result
        if isinstance(r, Result) and r.summary.startswith("Machine Metrics")
    ] == [State.OK]


def test_check_with_errored_handled_metadata_section() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.ERROR,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            cache_health=CacheHealth(
                container_metrics=CacheSizeInfo(size=150, maxsize=10000),
                machine_sections=CacheSizeInfo(size=4, maxsize=400),
            ),
        ),
        nodes=NodeMetadataFactory.batch(1),
    )
    collector_daemons = CollectorDaemonsFactory.build(
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        ),
    )

    # Act
    check_result = list(
        kube_collector_info.check(
            kube_collector_info.DEFAULT_PARAMS,
            collector_metadata,
            None,
            collector_daemons,
        )
    )

    # Assert
    assert len(check_result) == 3
    assert isinstance(check_result[0], Result) and check_result[0].state == State.CRIT


def test_check_with_errored_handled_component_section() -> None:
    # Arrange
    collector_processing_logs = CollectorProcessingLogs(
        container=CollectorHandlerLog(status=CollectorState.ERROR, title="title", detail="OK"),
        machine=CollectorHandlerLog(status=CollectorState.ERROR, title="title", detail="OK"),
    )

    # Act
    result = list(
        kube_collector_info._component_check(
            State.CRIT, "container_metrics", collector_processing_logs.container
        )
    )

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], Result)
    assert result[0].state == State.CRIT
    assert result[0].summary.startswith("Container Metrics: ")


def test_check_api_daemonsets_not_found() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            cache_health=CacheHealth(
                container_metrics=CacheSizeInfo(size=150, maxsize=10000),
                machine_sections=CacheSizeInfo(size=4, maxsize=400),
            ),
        ),
        nodes=None,
    )
    collector_daemons = CollectorDaemonsFactory.build(
        machine=None,
        container=None,
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        ),
    )
    collector_processing_logs = None

    # Act
    check_result = list(
        kube_collector_info.check(
            kube_collector_info.DEFAULT_PARAMS,
            collector_metadata,
            collector_processing_logs,
            collector_daemons,
        )
    )

    # Assert
    assert len(check_result) == 8
    container_result = check_result[1]
    machine_result = check_result[2]
    additional_info_result = check_result[3]
    assert isinstance(container_result, Result) and container_result.state == State.OK
    assert container_result.summary == "No DaemonSet with label node-collector=container-metrics"
    assert isinstance(machine_result, Result) and machine_result.state == State.OK
    assert machine_result.summary == "No DaemonSet with label node-collector=machine-sections"
    assert isinstance(additional_info_result, Result) and additional_info_result.state == State.OK
    assert additional_info_result.details.startswith("Collector DaemonSets")


def test_check_api_daemonsets_multiple_with_same_label() -> None:
    # Arrange
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(cache_health=None),
        nodes=None,
    )
    collector_daemons = CollectorDaemonsFactory.build(
        errors=IdentificationError(
            duplicate_machine_collector=True,
            duplicate_container_collector=True,
            unknown_collector=False,
        ),
    )
    collector_processing_logs = None

    # Act
    check_result = list(
        kube_collector_info.check(
            kube_collector_info.DEFAULT_PARAMS,
            collector_metadata,
            collector_processing_logs,
            collector_daemons,
        )
    )

    # Assert
    assert len(check_result) == 4
    container_result = check_result[1]
    machine_result = check_result[2]
    additional_info_result = check_result[3]
    assert isinstance(container_result, Result) and container_result.state == State.OK
    assert (
        container_result.summary
        == "Multiple DaemonSets with label node-collector=container-metrics"
    )
    assert isinstance(machine_result, Result) and machine_result.state == State.OK
    assert (
        machine_result.summary == "Multiple DaemonSets with label node-collector=machine-sections"
    )
    assert isinstance(additional_info_result, Result) and additional_info_result.state == State.OK
    assert (
        additional_info_result.details
        == "Cannot identify node collector, if label is found on multiple DaemonSets"
    )


@pytest.mark.parametrize(
    "cache_health, levels_container, levels_machine, expected",
    [
        pytest.param(
            CacheHealth(
                container_metrics=CacheSizeInfo(size=150, maxsize=10000),
                machine_sections=CacheSizeInfo(size=4, maxsize=400),
            ),
            ("percentage", ("no_levels", None)),
            ("percentage", ("no_levels", None)),
            [
                Result(state=State.OK, summary="Cluster collector version: 1.0.0"),
                Result(state=State.OK, summary="Nodes with container collectors: 1/1"),
                Result(state=State.OK, summary="Nodes with machine collectors: 1/1"),
                Result(
                    state=State.OK,
                    notice="Container metrics cache size: 1.50% - 150 of 10000 entries",
                ),
                Metric(
                    "kube_cluster_collector_container_metrics_cache_size",
                    150.0,
                    boundaries=(0.0, 10000.0),
                ),
                Result(state=State.OK, summary="Container Metrics: OK"),
                Result(
                    state=State.OK, notice="Machine sections cache size: 1.00% - 4 of 400 entries"
                ),
                Metric(
                    "kube_cluster_collector_machine_sections_cache_size",
                    4.0,
                    boundaries=(0.0, 400.0),
                ),
                Result(state=State.OK, summary="Machine Metrics: OK"),
            ],
            id="no levels",
        ),
        pytest.param(
            CacheHealth(
                container_metrics=CacheSizeInfo(size=9500, maxsize=10000),
                machine_sections=CacheSizeInfo(size=4, maxsize=400),
            ),
            ("percentage", ("fixed", (80.0, 95.0))),
            ("percentage", ("no_levels", None)),
            [
                Result(state=State.OK, summary="Cluster collector version: 1.0.0"),
                Result(state=State.OK, summary="Nodes with container collectors: 1/1"),
                Result(state=State.OK, summary="Nodes with machine collectors: 1/1"),
                Result(
                    state=State.CRIT,
                    notice="Container metrics cache size: 95.00% - 9500 of 10000 entries (warn at 80.00%, crit at 95.00%)",
                ),
                Metric(
                    "kube_cluster_collector_container_metrics_cache_size",
                    9500.0,
                    levels=(8000.0, 9500.0),
                    boundaries=(0.0, 10000.0),
                ),
                Result(state=State.OK, summary="Container Metrics: OK"),
                Result(
                    state=State.OK, notice="Machine sections cache size: 1.00% - 4 of 400 entries"
                ),
                Metric(
                    "kube_cluster_collector_machine_sections_cache_size",
                    4.0,
                    boundaries=(0.0, 400.0),
                ),
                Result(state=State.OK, summary="Machine Metrics: OK"),
            ],
            id="containers crit percentage",
        ),
        pytest.param(
            CacheHealth(
                container_metrics=CacheSizeInfo(size=9500, maxsize=10000),
                machine_sections=CacheSizeInfo(size=397, maxsize=400),
            ),
            ("absolute", ("fixed", (9000.0, 9700.0))),
            ("percentage", ("fixed", (90.0, 95.0))),
            [
                Result(state=State.OK, summary="Cluster collector version: 1.0.0"),
                Result(state=State.OK, summary="Nodes with container collectors: 1/1"),
                Result(state=State.OK, summary="Nodes with machine collectors: 1/1"),
                Result(
                    state=State.WARN,
                    notice="Container metrics cache size: 95.00% - 9500 of 10000 entries (warn at 9000, crit at 9700)",
                ),
                Metric(
                    "kube_cluster_collector_container_metrics_cache_size",
                    9500.0,
                    levels=(9000.0, 9700.0),
                    boundaries=(0.0, 10000.0),
                ),
                Result(state=State.OK, summary="Container Metrics: OK"),
                Result(
                    state=State.CRIT,
                    notice="Machine sections cache size: 99.25% - 397 of 400 entries (warn at 90.00%, crit at 95.00%)",
                ),
                Metric(
                    "kube_cluster_collector_machine_sections_cache_size",
                    397.0,
                    levels=(360.0, 380.0),
                    boundaries=(0.0, 400.0),
                ),
                Result(state=State.OK, summary="Machine Metrics: OK"),
            ],
            id="mixed absolute and percentage, both alert with correct format",
        ),
        pytest.param(
            None,
            ("absolute", ("fixed", (9000.0, 9700.0))),
            ("percentage", ("fixed", (90.0, 95.0))),
            [
                Result(state=State.OK, summary="Cluster collector version: 1.0.0"),
                Result(state=State.OK, summary="Nodes with container collectors: 1/1"),
                Result(state=State.OK, summary="Nodes with machine collectors: 1/1"),
                Result(state=State.OK, summary="Container Metrics: OK"),
                Result(state=State.OK, summary="Machine Metrics: OK"),
            ],
            id="missing cache health stats (support old dist. piggyback versions)",
        ),
    ],
)
def test_check_cache_health_scenarios(
    cache_health: CacheHealth | None,
    levels_container: tuple[kube_collector_info.CacheSizeMode, LevelsT[float] | LevelsT[int]],
    levels_machine: tuple[kube_collector_info.CacheSizeMode, LevelsT[float] | LevelsT[int]],
    expected: CheckResult,
) -> None:
    collector_metadata = CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK,
            title="title",
            detail="detail",
        ),
        cluster_collector=ClusterCollectorMetadataFactory.build(
            node=NodeName("cool-node"),
            host_name=HostName("cool-node.example.com"),
            container_platform=PlatformMetadata(
                os_name=OsName("Linux"),
                os_version=Version("3.133.7"),
                python_version=Version("3.14"),
                python_compiler=PythonCompiler("GCC 1337"),
            ),
            checkmk_kube_agent=CheckmkKubeAgentMetadata(
                project_version=Version("1.0.0"),
            ),
            cache_health=cache_health,
        ),
        nodes=None,
    )
    collector_daemons = CollectorDaemons(
        container=NodeCollectorReplica(available=1, desired=1),
        machine=NodeCollectorReplica(available=1, desired=1),
        errors=IdentificationError(
            duplicate_machine_collector=False,
            duplicate_container_collector=False,
            unknown_collector=False,
        ),
    )
    collector_processing_logs = CollectorProcessingLogs(
        container=CollectorHandlerLog(status=CollectorState.OK, title="OK", detail=None),
        machine=CollectorHandlerLog(status=CollectorState.OK, title="OK", detail=None),
    )
    check_result = list(
        kube_collector_info.check(
            {
                **kube_collector_info.DEFAULT_PARAMS,
                "container_metrics_cache_size": levels_container,
                "machine_sections_cache_size": levels_machine,
            },
            collector_metadata,
            collector_processing_logs,
            collector_daemons,
        )
    )
    assert check_result == expected
