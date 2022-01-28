#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest

from cmk.base.plugins.agent_based import kube_cpu_usage
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, render, Result, State
from cmk.base.plugins.agent_based.utils import kube_resources

USAGE = 0.08917935971914392879  # value for cpu usage (Germain & Cunningham)
LEVELS = 60.0, 90.0  # default values for upper levels
OK = 0.18  # value for request and limit to set state to OK
WARN = 0.12  # value for request and limit to set state to WARN
CRIT = 0.09  # value for request and limit to set state to CRIT

# Resources
LIMIT = 2 * OK
REQUEST = OK
COUNT_TOTAL = 2
COUNT_UNSPECIFIED_REQUESTS = 0
COUNT_UNSPECIFIED_LIMITS = 0
COUNT_ZEROED_LIMITS = 0


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
def params(params_usage, params_request, params_limit):
    return kube_cpu_usage.Params(usage=params_usage, request=params_request, limit=params_limit)


@pytest.fixture
def usage_usage():
    return USAGE


@pytest.fixture
def usage_string_table_element(usage_usage):
    return {"usage": usage_usage}


@pytest.fixture
def usage_string_table(usage_string_table_element):
    return [[json.dumps(usage_string_table_element)]]


@pytest.fixture
def usage_section(usage_string_table):
    return kube_cpu_usage.parse_kube_performance_cpu_v1(usage_string_table)


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
    return kube_cpu_usage.parse_resources(resources_string_table)


@pytest.fixture
def check_result(params, usage_section, resources_section):
    return kube_cpu_usage.check_kube_cpu(params, usage_section, resources_section)


def test_parse_kube_cpu_resources_v1(resources_string_table, resources_request, resources_limit):
    resources_section = kube_cpu_usage.parse_resources(resources_string_table)
    assert resources_section.request == resources_request
    assert resources_section.limit == resources_limit


def test_discovery(usage_section, resources_section):
    assert len(list(kube_cpu_usage.discovery_kube_cpu(usage_section, None))) == 1
    assert len(list(kube_cpu_usage.discovery_kube_cpu(None, resources_section))) == 1
    assert len(list(kube_cpu_usage.discovery_kube_cpu(None, None))) == 1
    assert len(list(kube_cpu_usage.discovery_kube_cpu(usage_section, resources_section))) == 1


@pytest.mark.parametrize("usage_section", [None])
def test_check_missing_usage(check_result):
    assert len(list(check_result)) == 4


def test_count_metrics_all_sections_present(check_result):
    assert len([r for r in check_result if isinstance(r, Metric)]) == 5


def test_count_results_all_sections_present(check_result):
    assert len([r for r in check_result if isinstance(r, Result)]) == 3


@pytest.mark.parametrize("usage_section", [None])
def test_check_results_without_usage(check_result):
    expected_beginnings = ["Request: 0.180", "Limit: 0.360"]
    results = [r for r in check_result if isinstance(r, Result)]
    assert all(
        r.summary.startswith(beginning) for r, beginning in zip(results, expected_beginnings)
    )
    assert all(r.state == State.OK for r in results)


@pytest.mark.parametrize("usage_section", [None])
def test_check_metrics_without_usage(check_result):
    expected_metrics = {
        Metric("kube_cpu_request", 0.18, boundaries=(0.0, None)),
        Metric("kube_cpu_limit", 0.36, boundaries=(0.0, None)),
    }
    metrics = {r for r in check_result if isinstance(r, Metric)}
    assert expected_metrics == metrics


@pytest.mark.parametrize("resources_section", [None])
def test_check_if_no_resources(check_result):
    """Crashing is expected, because section_kube_cpu_usage is only missing, if data from the api
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
        f"Request utilization: {render.percent(USAGE /  resources_request * 100)} - {USAGE:0.3f} of {resources_request:0.3f}",
        f"Limit utilization: {render.percent(USAGE / resources_limit * 100)} - {USAGE:0.3f} of {resources_limit:0.3f}",
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
    ]
    assert [(m.name, m.value) for m in check_result if isinstance(m, Metric)] == expected


def test_check_all_states_ok(check_result):
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
def test_check_all_states_ok_params_ignore(check_result):
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
            [State.WARN, State.OK, State.OK],
        ),
        (
            ("no_levels", (0.01, 0.01)),
            "no_levels",
            "no_levels",
            [State.CRIT, State.OK, State.OK],
        ),
    ],
)
def test_check_abs_levels_with_mixed(expected_states, check_result):
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


@pytest.mark.parametrize(
    "resources_request, resources_limit, expected_states",
    [
        (OK, 2 * OK, [State.OK, State.OK, State.OK]),
        (OK, 2 * WARN, [State.OK, State.OK, State.WARN]),
        (OK, 2 * CRIT, [State.OK, State.OK, State.CRIT]),
        (WARN, 2 * OK, [State.OK, State.WARN, State.OK]),
        (CRIT, 2 * OK, [State.OK, State.CRIT, State.OK]),
        (WARN, 2 * WARN, [State.OK, State.WARN, State.WARN]),
        (WARN, 2 * CRIT, [State.OK, State.WARN, State.CRIT]),
        (CRIT, 2 * WARN, [State.OK, State.CRIT, State.WARN]),
        (CRIT, 2 * CRIT, [State.OK, State.CRIT, State.CRIT]),
    ],
)
def test_check_result_states_mixed(expected_states, check_result):
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
