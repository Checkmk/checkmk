#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import itertools
from collections.abc import Sequence

import pytest

import cmk.base.plugins.agent_based.utils.kube
from cmk.base.plugins.agent_based import kube_cpu
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, render, Result, State
from cmk.base.plugins.agent_based.utils import kube_resources
from cmk.base.plugins.agent_based.utils.kube import Cpu, PerformanceUsage

ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE
TIMESTAMP = 359

USAGE = 0.08917935971914392879  # value for cpu usage (Germain & Cunningham)
OK = 0.18  # value for request and limit to set state to OK
WARN = 0.12  # value for request and limit to set state to WARN
CRIT = 0.09  # value for request and limit to set state to CRIT
ALLOCATABLE = 5.0  # value for allocatable cpu


# Resources
LIMIT = 2 * OK
REQUEST = OK


@pytest.fixture
def usage_section():
    return PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE))


@pytest.fixture
def params():
    return kube_resources.Params(
        usage="no_levels",
        request=("levels", (60.0, 90.0)),
        limit=("levels", (30.0, 45.0)),
        node=("levels", (15.0, 22.5)),
        cluster=("levels", (15.0, 22.5)),
    )


@pytest.fixture
def resources_request():
    return REQUEST


@pytest.fixture
def resources_limit():
    return LIMIT


@pytest.fixture
def resources_section(resources_request, resources_limit):
    return kube_resources.Resources(
        request=resources_request,
        limit=resources_limit,
        count_total=2,
        count_zeroed_limits=0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
    )


ALLOCATABLE_RESOURCE_SECTION = kube_resources.AllocatableResource(context="node", value=ALLOCATABLE)


def test_discovery(
    usage_section: cmk.base.plugins.agent_based.utils.kube.PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    for s1, s2, s3 in itertools.product(
        (usage_section, None), (resources_section, None), (ALLOCATABLE_RESOURCE_SECTION, None)
    ):
        assert len(list(kube_cpu.discovery_kube_cpu(s1, s2, s3))) == 1


def test_check_results_without_usage(params, resources_section):
    expected_beginnings = ["Requests: 0.180", "Limits: 0.360"]
    check_result = kube_cpu._check_kube_cpu(
        params, None, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert all(
        r.summary.startswith(beginning) for r, beginning in zip(results, expected_beginnings)
    )
    assert all(r.state == State.OK for r in results)


def test_check_metrics_without_usage(
    params: kube_resources.Params,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, None, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    expected_metrics = {
        Metric("kube_cpu_allocatable", ALLOCATABLE, boundaries=(0.0, None)),
        Metric("kube_cpu_request", 0.18, boundaries=(0.0, None)),
        Metric("kube_cpu_limit", 0.36, boundaries=(0.0, None)),
    }
    metrics = {r for r in check_result if isinstance(r, Metric)}
    assert expected_metrics == metrics


def test_check_if_no_resources(
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
) -> None:
    """Crashing is expected, because section_kube_cpu is only missing, if data from the api
    server missing."""
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, None, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    with pytest.raises(AssertionError):
        list(check_result)


def test_check_beginning_of_summaries_with_all_sections_present(
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
    resources_request: int,
    resources_limit: int,
) -> None:
    expected_beginnings = [
        f"Usage: {USAGE:0.3f}",
        f"Requests utilization: {render.percent(USAGE /  resources_request * 100)} - {USAGE:0.3f} of {resources_request:0.3f}",
        f"Limits utilization: {render.percent(USAGE / resources_limit * 100)} - {USAGE:0.3f} of {resources_limit:0.3f}",
    ]
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert all(
        r.summary.startswith(beginning) for r, beginning in zip(results, expected_beginnings)
    )


def test_check_yields_multiple_metrics_with_values(
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
    resources_request: int,
    resources_limit: int,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    expected = [
        ("kube_cpu_usage", USAGE),
        ("kube_cpu_request", resources_request),
        ("kube_cpu_request_utilization", USAGE / resources_request * 100),
        ("kube_cpu_limit", resources_limit),
        ("kube_cpu_limit_utilization", USAGE / resources_limit * 100),
        ("kube_cpu_allocatable", ALLOCATABLE),
        ("kube_cpu_node_allocatable_utilization", USAGE / ALLOCATABLE * 100),
    ]
    assert [(m.name, m.value) for m in check_result if isinstance(m, Metric)] == expected


def test_check_all_states_ok(
    params,
    usage_section,
    resources_section,
):
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


@pytest.mark.parametrize(
    "resources_limit, resources_request",
    [
        (OK, OK),
        (WARN, WARN),
        (CRIT, CRIT),
    ],
)
def test_check_all_states_ok_params_ignore(
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        kube_resources.DEFAULT_PARAMS,
        usage_section,
        resources_section,
        ALLOCATABLE_RESOURCE_SECTION,
        1.0,
        {},
    )

    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


@pytest.mark.parametrize(
    "resources_limit, resources_request",
    [
        (OK, OK),
        (WARN, WARN),
        (CRIT, CRIT),
    ],
)
@pytest.mark.parametrize(
    "params, expected_states",
    [
        (
            kube_resources.Params(
                usage=("levels", (0.01, 1.0)),
                request="no_levels",
                limit="no_levels",
                cluster="no_levels",
                node="no_levels",
            ),
            [State.WARN, State.OK, State.OK, State.OK],
        ),
        (
            kube_resources.Params(
                usage=("levels", (0.01, 0.01)),
                request="no_levels",
                limit="no_levels",
                cluster="no_levels",
                node="no_levels",
            ),
            [State.CRIT, State.OK, State.OK, State.OK],
        ),
    ],
)
def test_check_abs_levels_with_mixed(
    params: kube_resources.Params,
    expected_states: Sequence[State],
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


@pytest.mark.parametrize(
    "resources_request, resources_limit, expected_states",
    [
        (OK, 2 * OK, [State.OK, State.OK, State.OK, State.OK]),
        (OK, 2 * WARN, [State.OK, State.OK, State.WARN, State.OK]),
        (OK, 2 * CRIT, [State.OK, State.OK, State.CRIT, State.OK]),
        (WARN, 2 * OK, [State.OK, State.WARN, State.OK, State.OK]),
        (CRIT, 2 * OK, [State.OK, State.CRIT, State.OK, State.OK]),
        (WARN, 2 * WARN, [State.OK, State.WARN, State.WARN, State.OK]),
        (WARN, 2 * CRIT, [State.OK, State.WARN, State.CRIT, State.OK]),
        (CRIT, 2 * WARN, [State.OK, State.CRIT, State.WARN, State.OK]),
        (CRIT, 2 * CRIT, [State.OK, State.CRIT, State.CRIT, State.OK]),
    ],
)
def test_check_result_states_mixed(
    expected_states: Sequence[State],
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


def test_overview_requests_contained_no_usage_section(
    params: kube_resources.Params,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, None, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    overview_requests_ignored = kube_resources.count_overview(resources_section, "request")
    results = [r for r in check_result if isinstance(r, Result)]
    requests_results = [r for r in results if "Request" in r.summary]
    assert len(requests_results) == 1
    assert [r for r in results if overview_requests_ignored in r.summary] == requests_results


def test_overview_requests_contained(
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, usage_section, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    overview_requests_ignored = kube_resources.count_overview(resources_section, "request")
    results = [r for r in check_result if isinstance(r, Result)]
    requests_results = [r for r in results if "Request" in r.summary]
    assert len(requests_results) == 1
    assert [r for r in results if overview_requests_ignored in r.summary] == requests_results


def test_overview_limits_contained_no_usage(
    params: kube_resources.Params,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, None, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    overview_limits_ignored = kube_resources.count_overview(resources_section, "limit")
    results = [r for r in check_result if isinstance(r, Result)]
    limits_results = [r for r in results if "Limit" in r.summary]
    assert len(limits_results) == 1
    assert [r for r in results if overview_limits_ignored in r.summary] == limits_results


def test_overview_limits_contained(
    params: kube_resources.Params,
    usage_section: PerformanceUsage,
    resources_section: kube_resources.Resources,
) -> None:
    check_result = kube_cpu._check_kube_cpu(
        params, None, resources_section, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    overview_limits_ignored = kube_resources.count_overview(resources_section, "limit")
    results = [r for r in check_result if isinstance(r, Result)]
    limits_results = [r for r in results if "Limit" in r.summary]
    assert len(limits_results) == 1
    assert [r for r in results if overview_limits_ignored in r.summary] == limits_results


def test_stored_usage_value() -> None:
    value_store = {
        "cpu_usage": (
            TIMESTAMP - ONE_MINUTE * 1,
            PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE)).json(),
        )
    }
    performance_cpu = cmk.base.plugins.agent_based.utils.kube_resources.performance_cpu(
        None, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is not None


def test_stored_outdated_usage_value() -> None:
    value_store = {
        "cpu_usage": (
            TIMESTAMP - ONE_MINUTE * 2,
            PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE)).json(),
        )
    }

    performance_cpu = cmk.base.plugins.agent_based.utils.kube_resources.performance_cpu(
        None, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is None
