#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Sequence

from tests.unit.cmk.special_agents.agent_kube.factory import PerformancePodFactory

from cmk.special_agents.agent_kube import (
    ContainerMetricsStore,
    ContainerName,
    CounterMetric,
    determine_rate_metrics,
    kube_object_performance_sections,
    map_lookup_name_to_piggyback_host_name,
    MetricName,
    pod_lookup_from_agent_pod,
    PodLookupName,
)
from cmk.special_agents.utils_kubernetes.schemata.section import PerformanceUsage


def counter_metric(metric_name: str, value: float, timestamp: float) -> CounterMetric:
    return CounterMetric(name=MetricName(metric_name), value=value, timestamp=timestamp)


def container_metrics_store(
    container_name: ContainerName, metrics: Sequence[CounterMetric]
) -> ContainerMetricsStore:
    return ContainerMetricsStore(
        name=container_name,
        metrics={metric.name: metric for metric in metrics},
    )


def test_determine_rate_metrics() -> None:
    metric_name = "metric"
    current_containers = container_metrics_store(
        container_name=ContainerName("container"),
        metrics=[counter_metric(metric_name=metric_name, value=1, timestamp=1)],
    )
    old_containers = container_metrics_store(
        container_name=ContainerName("container"),
        metrics=[counter_metric(metric_name=metric_name, value=1, timestamp=0)],
    )
    containers_rate_metrics = determine_rate_metrics(
        {current_containers.name: current_containers}, {old_containers.name: old_containers}
    )
    assert len(containers_rate_metrics) == 1
    assert len(containers_rate_metrics[ContainerName("container")]) == 1


def test_determine_rate_metrics_for_containers_with_same_timestamp() -> None:
    """Test that no rate metrics are returned if no rates can be determined."""
    timestamp = 0
    metric_name = "metric"
    current_containers = container_metrics_store(
        container_name=ContainerName("container"),
        metrics=[counter_metric(metric_name=metric_name, value=1, timestamp=timestamp)],
    )
    old_containers = container_metrics_store(
        container_name=ContainerName("container"),
        metrics=[counter_metric(metric_name=metric_name, value=1, timestamp=timestamp)],
    )

    containers_rate_metrics = determine_rate_metrics(
        {current_containers.name: current_containers}, {old_containers.name: old_containers}
    )
    assert len(containers_rate_metrics) == 0


def test_map_lookup_name_to_piggyback_host_name(new_pod) -> None:  # type:ignore[no-untyped-def]
    """Test that the namespace_name lookup name is used to find the piggyback host name"""
    pod = new_pod()
    pod_namespaced_name = PodLookupName(f"{pod.metadata.namespace}_{pod.metadata.name}")
    lookup_name_piggyback_mappings = map_lookup_name_to_piggyback_host_name(
        [pod], pod_lookup_from_agent_pod
    )
    assert pod_namespaced_name in lookup_name_piggyback_mappings
    assert lookup_name_piggyback_mappings[pod_namespaced_name] == pod.name(prepend_namespace=True)


def test_kube_object_performance_sections() -> None:
    performance_pods = [
        PerformancePodFactory.build(),
        PerformancePodFactory.build(),
    ]

    performance_sections = kube_object_performance_sections(performance_pods)

    assert [section[0] for section in performance_sections] == [
        "kube_performance_memory_v1",
        "kube_performance_cpu_v1",
    ]
    assert [PerformanceUsage(**json.loads(section[1])) for section in performance_sections]
