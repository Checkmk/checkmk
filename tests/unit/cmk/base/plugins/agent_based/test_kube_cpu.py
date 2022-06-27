#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import itertools
import json
from typing import Dict, Optional, Tuple

import pytest

import cmk.base.plugins.agent_based.utils.kube
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based import kube_cpu
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, render, Result, State
from cmk.base.plugins.agent_based.utils import kube_resources

ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE
TIMESTAMP = 359

USAGE = 0.08917935971914392879  # value for cpu usage (Germain & Cunningham)
LEVELS = 60.0, 90.0  # default values for upper levels for request and limit
OK = 0.18  # value for request and limit to set state to OK
WARN = 0.12  # value for request and limit to set state to WARN
CRIT = 0.09  # value for request and limit to set state to CRIT
ALLOCATABLE = 5.0  # value for allocatable cpu
ALLOCATABLE_OK = ALLOCATABLE / 0.5  # value for allocatable to set state to OK
ALLOCATABLE_WARN = ALLOCATABLE / 0.6  # value for allocatable to set state to WARN
ALLOCATABLE_CRIT = ALLOCATABLE / 0.9  # value for allocatable to set state to CRIT
LEVELS_ALLOCATABLE = USAGE  # default values for upper levels for allocatable


# Resources
LIMIT = 2 * OK
REQUEST = OK
COUNT_TOTAL = 2
COUNT_UNSPECIFIED_REQUESTS = 0
COUNT_UNSPECIFIED_LIMITS = 0
COUNT_ZEROED_LIMITS = 0


@pytest.fixture
def usage_cycle_age() -> int:
    return 2


@pytest.fixture
def value_store(
    usage_cycle_age: int, usage_string_table: StringTable
) -> Dict[str, Tuple[float, str]]:
    return {
        "cpu_usage": (
            TIMESTAMP - ONE_MINUTE * usage_cycle_age,
            kube_resources.parse_performance_usage(usage_string_table).json(),
        )
    }


@pytest.fixture
def params_usage():
    return "no_levels"


@pytest.fixture
def params_request():
    return ("levels", LEVELS)


@pytest.fixture
def params_limit():
    return ("levels", (LEVELS[0] / 2, LEVELS[1] / 2))


@pytest.fixture
def params_cluster():
    return ("levels", (LEVELS[0] / 4, LEVELS[1] / 4))


@pytest.fixture
def params_node():
    return ("levels", (LEVELS[0] / 4, LEVELS[1] / 4))


@pytest.fixture
def params(params_usage, params_request, params_limit, params_cluster, params_node):
    return kube_cpu.Params(
        usage=params_usage,
        request=params_request,
        limit=params_limit,
        cluster=params_cluster,
        node=params_node,
    )


@pytest.fixture
def usage_usage():
    return USAGE


@pytest.fixture
def usage_string_table_element(usage_usage):
    return {"resource": {"type_": "cpu", "usage": usage_usage}}


@pytest.fixture
def usage_string_table(usage_string_table_element) -> StringTable:
    return [[json.dumps(usage_string_table_element)]]


@pytest.fixture
def usage_section(usage_string_table):
    return kube_resources.parse_performance_usage(usage_string_table)


@pytest.fixture
def resources_request():
    return REQUEST


@pytest.fixture
def resources_limit():
    return LIMIT


@pytest.fixture
def resources_string_table_element(resources_request, resources_limit):
    return {
        "request": resources_request,
        "limit": resources_limit,
        "count_total": COUNT_TOTAL,
        "count_zeroed_limits": COUNT_ZEROED_LIMITS,
        "count_unspecified_limits": COUNT_UNSPECIFIED_LIMITS,
        "count_unspecified_requests": COUNT_UNSPECIFIED_REQUESTS,
    }


@pytest.fixture
def resources_string_table(resources_string_table_element):
    return [[json.dumps(resources_string_table_element)]]


@pytest.fixture
def resources_section(resources_string_table):
    return kube_cpu.parse_resources(resources_string_table)


@pytest.fixture
def overview_limits_ignored(resources_section):
    return kube_resources.count_overview(resources_section, "limit")


@pytest.fixture
def overview_requests_ignored(resources_section):
    return kube_resources.count_overview(resources_section, "request")


@pytest.fixture
def allocatable_value():
    return ALLOCATABLE


@pytest.fixture
def allocatable_resource_string_table_element(allocatable_value):
    return {"context": "node", "value": allocatable_value}


@pytest.fixture
def allocatable_resource_string_table(allocatable_resource_string_table_element):
    return [[json.dumps(allocatable_resource_string_table_element)]]


@pytest.fixture
def allocatable_resource_section(allocatable_resource_string_table):
    return kube_cpu.parse_allocatable_resource(allocatable_resource_string_table)


@pytest.fixture
def check_result(params, usage_section, resources_section, allocatable_resource_section):
    return kube_cpu.check_kube_cpu(
        params, usage_section, resources_section, allocatable_resource_section
    )


def test_parse_resources(resources_string_table, resources_request, resources_limit) -> None:
    resources_section = kube_cpu.parse_resources(resources_string_table)
    assert resources_section.request == resources_request
    assert resources_section.limit == resources_limit


def test_parse_allocatable_resource(allocatable_resource_string_table, allocatable_value) -> None:
    allocatable_resource_section = kube_cpu.parse_allocatable_resource(
        allocatable_resource_string_table
    )
    assert allocatable_resource_section.value == allocatable_value


def test_discovery(usage_section, resources_section, allocatable_resource_section) -> None:
    for s1, s2, s3 in itertools.product(
        (usage_section, None), (resources_section, None), (allocatable_resource_section, None)
    ):
        assert len(list(kube_cpu.discovery_kube_cpu(s1, s2, s3))) == 1


@pytest.mark.parametrize("usage_section", [None])
def test_check_missing_usage(check_result) -> None:
    assert len(list(check_result)) == 6


def test_count_metrics_all_sections_present(check_result) -> None:
    assert len([r for r in check_result if isinstance(r, Metric)]) == 7


def test_count_results_all_sections_present(check_result) -> None:
    assert len([r for r in check_result if isinstance(r, Result)]) == 4


def test_check_yields_check_results(check_result) -> None:
    assert len(list(check_result)) == 3 * 1 + 4 * 2


def test_check_yields_results(check_result) -> None:
    expected = 1 + 2 + 1
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


@pytest.mark.parametrize("usage_section", [None])
def test_check_results_without_usage(check_result) -> None:
    expected_beginnings = ["Requests: 0.180", "Limits: 0.360"]
    results = [r for r in check_result if isinstance(r, Result)]
    assert all(
        r.summary.startswith(beginning) for r, beginning in zip(results, expected_beginnings)
    )
    assert all(r.state == State.OK for r in results)


@pytest.mark.parametrize("usage_section", [None])
def test_check_metrics_without_usage(check_result) -> None:
    expected_metrics = {
        Metric("kube_cpu_allocatable", ALLOCATABLE, boundaries=(0.0, None)),
        Metric("kube_cpu_request", 0.18, boundaries=(0.0, None)),
        Metric("kube_cpu_limit", 0.36, boundaries=(0.0, None)),
    }
    metrics = {r for r in check_result if isinstance(r, Metric)}
    assert expected_metrics == metrics


@pytest.mark.parametrize("resources_section", [None])
def test_check_if_no_resources(check_result) -> None:
    """Crashing is expected, because section_kube_cpu is only missing, if data from the api
    server missing."""
    with pytest.raises(AssertionError):
        list(check_result)


def test_check_beginning_of_summaries_with_all_sections_present(
    check_result,
    resources_request,
    resources_limit,
):
    expected_beginnings = [
        f"Usage: {USAGE:0.3f}",
        f"Requests utilization: {render.percent(USAGE /  resources_request * 100)} - {USAGE:0.3f} of {resources_request:0.3f}",
        f"Limits utilization: {render.percent(USAGE / resources_limit * 100)} - {USAGE:0.3f} of {resources_limit:0.3f}",
    ]
    results = [r for r in check_result if isinstance(r, Result)]
    assert all(
        r.summary.startswith(beginning) for r, beginning in zip(results, expected_beginnings)
    )


def test_check_yields_multiple_metrics_with_values(
    check_result, resources_request, resources_limit
):
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


def test_check_all_states_ok(check_result) -> None:
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


@pytest.mark.parametrize(
    "resources_limit, resources_request",
    [
        (OK, OK),
        (WARN, WARN),
        (CRIT, CRIT),
    ],
)
@pytest.mark.parametrize("params_request, params_limit", [(("no_levels"), ("no_levels"))])
def test_check_all_states_ok_params_ignore(check_result) -> None:
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
    "params_usage, params_request, params_limit, expected_states",
    [
        (
            ("no_levels", (0.01, 1.0)),
            "no_levels",
            "no_levels",
            [State.WARN, State.OK, State.OK, State.OK],
        ),
        (
            ("no_levels", (0.01, 0.01)),
            "no_levels",
            "no_levels",
            [State.CRIT, State.OK, State.OK, State.OK],
        ),
    ],
)
def test_check_abs_levels_with_mixed(expected_states, check_result) -> None:
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
def test_check_result_states_mixed(expected_states, check_result) -> None:
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


@pytest.mark.parametrize("usage_section", [None])
def test_overview_requests_contained_no_usage_section(
    usage_section, check_result, resources_section
) -> None:
    overview_requests_ignored = kube_resources.count_overview(resources_section, "request")
    results = [r for r in check_result if isinstance(r, Result)]
    requests_results = [r for r in results if "Request" in r.summary]
    assert len(requests_results) == 1
    assert [r for r in results if overview_requests_ignored in r.summary] == requests_results


def test_overview_requests_contained(usage_section, check_result, resources_section) -> None:
    overview_requests_ignored = kube_resources.count_overview(resources_section, "request")
    results = [r for r in check_result if isinstance(r, Result)]
    requests_results = [r for r in results if "Request" in r.summary]
    assert len(requests_results) == 1
    assert [r for r in results if overview_requests_ignored in r.summary] == requests_results


@pytest.mark.parametrize("usage_section", [None])
def test_overview_limits_contained_no_usage(usage_section, check_result, resources_section) -> None:
    overview_limits_ignored = kube_resources.count_overview(resources_section, "limit")
    results = [r for r in check_result if isinstance(r, Result)]
    limits_results = [r for r in results if "Limit" in r.summary]
    assert len(limits_results) == 1
    assert [r for r in results if overview_limits_ignored in r.summary] == limits_results


def test_overview_limits_contained(usage_section, check_result, resources_section) -> None:
    overview_limits_ignored = kube_resources.count_overview(resources_section, "limit")
    results = [r for r in check_result if isinstance(r, Result)]
    limits_results = [r for r in results if "Limit" in r.summary]
    assert len(limits_results) == 1
    assert [r for r in results if overview_limits_ignored in r.summary] == limits_results


@pytest.mark.parametrize("usage_cycle_age", [1])
@pytest.mark.parametrize("usage_section", [None])
def test_stored_usage_value(
    usage_section: Optional[cmk.base.plugins.agent_based.utils.kube.PerformanceUsage], value_store
):
    performance_cpu = cmk.base.plugins.agent_based.utils.kube_resources.performance_cpu(
        usage_section, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is not None


@pytest.mark.parametrize("usage_section", [None])
def test_stored_outdated_usage_value(
    usage_section: Optional[cmk.base.plugins.agent_based.utils.kube.PerformanceUsage], value_store
):
    performance_cpu = cmk.base.plugins.agent_based.utils.kube_resources.performance_cpu(
        usage_section, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is None
