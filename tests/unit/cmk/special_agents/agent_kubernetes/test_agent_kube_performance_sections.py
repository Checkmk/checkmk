#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence

from cmk.special_agents.agent_kube import (
    group_containers_by_pods,
    group_metrics_by_containers,
    MetricName,
    PerformanceContainer,
    PodUID,
)
from cmk.special_agents.utils_kubernetes.schemata.section import ContainerName, PerformanceMetric


def _performance_container(
    container_name: str, pod_name, metrics: Sequence[str]
) -> PerformanceContainer:
    return PerformanceContainer(
        name=ContainerName(container_name),
        metrics={
            MetricName(metric): PerformanceMetric(value=0.0, timestamp=0) for metric in metrics
        },
        pod_uid=PodUID(pod_name),
    )


def test_group_metrics_by_containers():
    cluster_resp = [
        {
            "container_name": "container",
            "pod_uid": "pod",
            "metric_name": "container_memory_usage_bytes_total",
            "metric_value_string": "0 1637672238173",
        },
        {
            "container_name": "container",
            "pod_uid": "pod",
            "metric_name": "container_memory_swap",
            "metric_value_string": "0 1637672238173",
        },
    ]
    containers = group_metrics_by_containers(cluster_resp)
    assert len(containers) == 1
    assert isinstance(containers[0], PerformanceContainer)
    assert len(containers[0].metrics) == 2
    assert containers[0].pod_uid == "pod"


def test_containers_by_pods():
    pod_names = ["pod_one", "pod_two"]
    container_per_pod_count = 2
    containers = [
        _performance_container(
            f"container_{i}",
            pod_name=pod,
            metrics=["memory_usage"],
        )
        for pod in pod_names
        for i in range(container_per_pod_count)
    ]
    pods = group_containers_by_pods(containers)
    assert len(pods) == len(pod_names)
    assert all(pod_name in pods for pod_name in pod_names)
    assert all(len(pod.containers) == container_per_pod_count for pod in pods.values())
