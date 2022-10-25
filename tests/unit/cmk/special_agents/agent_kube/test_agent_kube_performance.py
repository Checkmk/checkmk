#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.unit.cmk.special_agents.agent_kube.factory import (
    PerformanceMetricFactory,
    PerformancePodFactory,
)

from cmk.special_agents.utils_kubernetes.performance import (
    _determine_rate_metrics,
    _kube_object_performance_sections,
)
from cmk.special_agents.utils_kubernetes.schemata.section import PerformanceUsage


def test_determine_rate_metrics() -> None:
    current_cpu_metric = PerformanceMetricFactory.build(timestamp=1)
    old_cpu_metric = current_cpu_metric.copy()
    old_cpu_metric.timestamp = 0
    containers_rate_metrics = _determine_rate_metrics([current_cpu_metric], [old_cpu_metric])
    assert len(containers_rate_metrics) == 1
    assert len(containers_rate_metrics[current_cpu_metric.container_name]) == 1


def test_determine_rate_metrics_for_containers_with_same_timestamp() -> None:
    """Test that no rate metrics are returned if no rates can be determined."""
    cpu_metric = PerformanceMetricFactory.build()
    containers_rate_metrics = _determine_rate_metrics([cpu_metric], [cpu_metric])
    assert len(containers_rate_metrics) == 0


def test_kube_object_performance_sections() -> None:
    performance_pods = [
        PerformancePodFactory.build(),
        PerformancePodFactory.build(),
    ]

    performance_sections = _kube_object_performance_sections(performance_pods)

    assert [section[0] for section in performance_sections] == [
        "kube_performance_memory_v1",
        "kube_performance_cpu_v1",
    ]
    assert [PerformanceUsage.parse_raw(section[1]) for section in performance_sections]
