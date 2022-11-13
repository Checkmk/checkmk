#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.unit.cmk.special_agents.agent_kube.factory import MemoryMetricFactory

from cmk.special_agents.utils_kubernetes.common import lookup_name
from cmk.special_agents.utils_kubernetes.performance import (
    _group_container_metrics_by_pods,
    PerformancePod,
)


def test_group_metrics_by_containers() -> None:
    memory_metric = MemoryMetricFactory.build()
    expected = {
        memory_metric.pod_lookup_from_metric(): PerformancePod(memory=memory_metric.value, cpu=0.0)
    }
    assert expected == _group_container_metrics_by_pods(
        cpu_metrics=[], memory_metrics=[memory_metric]
    )


def test_containers_by_pods() -> None:
    pod_names = ["pod_one", "pod_two"]
    memory_metrics = [
        m
        for pod_name in pod_names
        for m in MemoryMetricFactory.batch(size=2, pod_name=pod_name, namespace="default")
    ]
    pods = _group_container_metrics_by_pods(cpu_metrics=[], memory_metrics=memory_metrics)
    assert len(pods) == 2
    assert all(lookup_name("default", pod_name) in pods for pod_name in pod_names)
