#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.kube.agent_based.kube_memory import check_kube_memory, discovery_kube_memory
from cmk.plugins.kube.kube_resources import count_overview, DEFAULT_PARAMS, Params
from cmk.plugins.kube.schemata.section import (
    AllocatableResource,
    Memory,
    PerformanceUsage,
    Resources,
)


def test_discovery() -> None:
    resources = Resources(
        request=0.0,
        limit=0.0,
        count_unspecified_limits=0,
        count_zeroed_limits=0,
        count_unspecified_requests=0,
        count_total_requests=0,
        count_total_limits=0,
        count_pods_pod_level_request=0,
        count_pods_pod_level_limit=0,
    )
    assert list(discovery_kube_memory(None, resources, None))


@pytest.mark.parametrize(
    "section_kube_memory_resources,section_kube_performance_memory,expected_result",
    [
        pytest.param(
            Resources(
                request=0.0,
                limit=28120704.0,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_unspecified_requests=0,
                count_total_requests=2,
                count_total_limits=2,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            None,
            (
                Result(state=State.OK, summary="Requests: 0 B (2/2 containers with requests)"),
                Metric("kube_memory_request", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Limits: 26.8 MiB (2/2 containers with limits)"),
                Metric("kube_memory_limit", 28120704.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Allocatable: 34.3 MiB"),
                Metric("kube_memory_allocatable", 35917989.0, boundaries=(0.0, None)),
            ),
            id="No performance data",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=0.0,
                count_unspecified_limits=0,
                count_zeroed_limits=2,
                count_unspecified_requests=0,
                count_total_requests=2,
                count_total_limits=2,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            PerformanceUsage(resource=Memory(usage=18120704.0)),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Requests: 0 B (2/2 containers with requests)"),
                Metric("kube_memory_request", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Limits: 0 B (0/2 containers with limits)"),
                Metric("kube_memory_limit", 0.0, boundaries=(0.0, None)),
                Metric("kube_memory_allocatable", 35917989.0),
                Result(state=State.OK, summary="Node utilization: 50.45% - 17.3 MiB of 34.3 MiB"),
                Metric(
                    "kube_memory_node_allocatable_utilization",
                    50.45021869125245,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
            id="Weird config data set to zero",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=28120704.0,
                count_unspecified_limits=1,
                count_zeroed_limits=0,
                count_unspecified_requests=1,
                count_total_requests=2,
                count_total_limits=2,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            PerformanceUsage(resource=Memory(usage=18120704.0)),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Requests: 0 B (1/2 containers with requests)"),
                Metric("kube_memory_request", 0.0, boundaries=(0.0, None)),
                Metric("kube_memory_limit", 28120704.0),
                Result(
                    state=State.OK,
                    summary="Limits utilization: 64.44% - 17.3 MiB of 26.8 MiB (1/2 containers with limits)",
                ),
                Metric(
                    "kube_memory_limit_utilization",
                    64.4390126221591,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_allocatable", 35917989.0),
                Result(state=State.OK, summary="Node utilization: 50.45% - 17.3 MiB of 34.3 MiB"),
                Metric(
                    "kube_memory_node_allocatable_utilization",
                    50.45021869125245,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
            id="Config data not defined for at least container",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=28120704.0,
                count_unspecified_limits=1,
                count_zeroed_limits=1,
                count_unspecified_requests=2,
                count_total_requests=3,
                count_total_limits=3,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            PerformanceUsage(resource=Memory(usage=18120704.0)),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0, boundaries=(0.0, None)),
                Result(
                    state=State.OK,
                    summary="Requests: 0 B (1/3 containers with requests)",
                ),
                Metric("kube_memory_request", 0.0, boundaries=(0.0, None)),
                Metric("kube_memory_limit", 28120704.0),
                Result(
                    state=State.OK,
                    summary="Limits utilization: 64.44% - 17.3 MiB of 26.8 MiB (1/3 containers with limits)",
                ),
                Metric(
                    "kube_memory_limit_utilization",
                    64.4390126221591,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_allocatable", 35917989.0),
                Result(state=State.OK, summary="Node utilization: 50.45% - 17.3 MiB of 34.3 MiB"),
                Metric(
                    "kube_memory_node_allocatable_utilization",
                    50.45021869125245,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
            id="Config data not defined, and limit value is zero",
        ),
        pytest.param(
            Resources(
                request=13120704.0,
                limit=28120704.0,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_unspecified_requests=0,
                count_total_requests=2,
                count_total_limits=2,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            PerformanceUsage(resource=Memory(usage=18120704.0)),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0, boundaries=(0.0, None)),
                Metric("kube_memory_request", 13120704.0),
                Result(
                    state=State.OK,
                    summary="Requests utilization: 138.11% - 17.3 MiB of 12.5 MiB (2/2 containers with requests)",
                ),
                Metric(
                    "kube_memory_request_utilization", 138.10771129354035, boundaries=(0.0, None)
                ),
                Metric("kube_memory_limit", 28120704.0),
                Result(
                    state=State.OK,
                    summary="Limits utilization: 64.44% - 17.3 MiB of 26.8 MiB (2/2 containers with limits)",
                ),
                Metric(
                    "kube_memory_limit_utilization",
                    64.4390126221591,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_allocatable", 35917989.0),
                Result(state=State.OK, summary="Node utilization: 50.45% - 17.3 MiB of 34.3 MiB"),
                Metric(
                    "kube_memory_node_allocatable_utilization",
                    50.45021869125245,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
            id="All config data present, usage below request, this is the desirable state for a cluster",
        ),
        pytest.param(
            Resources(
                request=13120704.0,
                limit=28120704.0,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_unspecified_requests=0,
                count_total_requests=2,
                count_total_limits=2,
                count_pods_pod_level_request=0,
                count_pods_pod_level_limit=0,
            ),
            PerformanceUsage(resource=Memory(usage=27120704.0)),
            (
                Result(state=State.OK, summary="Usage: 25.9 MiB"),
                Metric("kube_memory_usage", 27120704.0, boundaries=(0.0, None)),
                Metric("kube_memory_request", 13120704.0),
                Result(
                    state=State.OK,
                    summary="Requests utilization: 206.70% - 25.9 MiB of 12.5 MiB (2/2 containers with requests)",
                ),
                Metric(
                    "kube_memory_request_utilization", 206.70159162191297, boundaries=(0.0, None)
                ),
                Metric("kube_memory_limit", 28120704.0),
                Result(
                    state=State.CRIT,
                    summary="Limits utilization: 96.44% - 25.9 MiB of 26.8 MiB (warn/crit at 80.00%/90.00%) (2/2 containers with limits)",
                ),
                Metric(
                    "kube_memory_limit_utilization",
                    96.44390126221592,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_allocatable", 35917989.0),
                Result(state=State.OK, summary="Node utilization: 75.51% - 25.9 MiB of 34.3 MiB"),
                Metric(
                    "kube_memory_node_allocatable_utilization",
                    75.50730081241464,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
            id="All config data present, usage above levels for limit",
        ),
    ],
)
def test_check_kube_memory(
    section_kube_performance_memory: PerformanceUsage | None,
    section_kube_memory_resources: Resources | None,
    expected_result: tuple[Result | Metric, ...],
) -> None:
    section_kube_memory_allocatable_resource = AllocatableResource(context="node", value=35917989.0)
    assert expected_result == tuple(
        check_kube_memory(
            Params(
                usage="no_levels",
                request="no_levels",
                limit=("levels", (80.0, 90.0)),
                cluster=("levels", (80.0, 90.0)),
                node=("levels", (80.0, 90.0)),
            ),
            section_kube_performance_memory,
            section_kube_memory_resources,
            section_kube_memory_allocatable_resource,
        )
    )


@pytest.mark.parametrize(
    "section_kube_performance_memory",
    [
        pytest.param(
            PerformanceUsage(resource=Memory(usage=18120704.0)),
            id="With usage",
        ),
        pytest.param(
            None,
            id="Without usage",
        ),
    ],
)
def test_no_results_if_no_resources(
    section_kube_performance_memory: PerformanceUsage | None,
) -> None:
    """
    No results expected when section_kube_memory is missing,
    e.g. if the API server is unreachable or during upgrades.
    """
    result = list(
        check_kube_memory(
            DEFAULT_PARAMS,
            section_kube_performance_memory,
            None,
            AllocatableResource(context="node", value=35917989.0),
        )
    )
    assert result == []


@pytest.mark.parametrize(
    "resources,requirement,expected",
    [
        pytest.param(
            Resources(
                request=3.0,
                limit=0.0,
                count_unspecified_requests=0,
                count_total_requests=0,
                count_pods_pod_level_request=1,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_total_limits=0,
                count_pods_pod_level_limit=0,
            ),
            "request",
            "1 pod with pod-level requests",
            id="only pod-level",
        ),
        pytest.param(
            Resources(
                request=4.0,
                limit=0.0,
                count_unspecified_requests=0,
                count_total_requests=1,
                count_pods_pod_level_request=1,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_total_limits=0,
                count_pods_pod_level_limit=0,
            ),
            "request",
            "1/1 containers with requests, 1 pod with pod-level requests",
            id="mixed",
        ),
        pytest.param(
            Resources(
                request=7.0,
                limit=0.0,
                count_unspecified_requests=0,
                count_total_requests=1,
                count_pods_pod_level_request=2,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_total_limits=0,
                count_pods_pod_level_limit=0,
            ),
            "request",
            "1/1 containers with requests, 2 pods with pod-level requests",
            id="plural pods",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=5.0,
                count_unspecified_requests=0,
                count_total_requests=0,
                count_pods_pod_level_request=0,
                count_unspecified_limits=0,
                count_zeroed_limits=0,
                count_total_limits=0,
                count_pods_pod_level_limit=1,
            ),
            "limit",
            "1 pod with pod-level limits",
            id="only pod-level limits",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=8.0,
                count_unspecified_requests=0,
                count_total_requests=0,
                count_pods_pod_level_request=0,
                count_unspecified_limits=0,
                count_zeroed_limits=1,
                count_total_limits=2,
                count_pods_pod_level_limit=2,
            ),
            "limit",
            "1/2 containers with limits, 2 pods with pod-level limits",
            id="mixed limits",
        ),
    ],
)
def test_count_overview_pod_level(
    resources: Resources,
    requirement: Literal["request", "limit", "allocatable"],
    expected: str,
) -> None:
    assert count_overview(resources, requirement) == expected
