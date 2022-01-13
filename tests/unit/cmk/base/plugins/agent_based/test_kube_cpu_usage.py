#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import itertools
import json

import pytest

from cmk.base.plugins.agent_based import kube_cpu_usage
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, render, Result, State
from cmk.base.plugins.agent_based.utils.kube_resources import ExceptionalResource

USAGE = 0.08917935971914392879  # value for cpu usage (Germain & Cunningham)
LEVELS = 60.0, 90.0  # default values for upper levels
OK = 0.18  # value for request and limit to set state to OK
WARN = 0.12  # value for request and limit to set state to WARN
CRIT = 0.09  # value for request and limit to set state to CRIT


@pytest.fixture
def params_request():
    return ("perc_used", LEVELS)


@pytest.fixture
def params_limit():
    return ("perc_used", (LEVELS[0] / 2, LEVELS[1] / 2))


@pytest.fixture
def params(params_request, params_limit):
    return kube_cpu_usage.Params(request=params_request, limit=params_limit)


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
    return kube_cpu_usage.parse_kube_live_cpu_usage_v1(usage_string_table)


@pytest.fixture
def state():
    return OK


@pytest.fixture
def state_request(state):
    return state


@pytest.fixture
def state_limit(state):
    return state


@pytest.fixture
def resources_request(state_request):
    return state_request


@pytest.fixture
def resources_limit(state_limit):
    return state_limit * 2


@pytest.fixture
def resources_string_table_element(resources_request, resources_limit):
    return {"request": resources_request, "limit": resources_limit}


@pytest.fixture
def resources_string_table(resources_string_table_element):
    return [[json.dumps(resources_string_table_element)]]


@pytest.fixture
def resources_section(resources_string_table):
    return kube_cpu_usage.parse_kube_cpu_resources_v1(resources_string_table)


@pytest.fixture
def check_result(params, usage_section, resources_section):
    return kube_cpu_usage.check(params, usage_section, resources_section)


def test_parse_kube_cpu_resources_v1(resources_string_table, resources_request, resources_limit):
    resources_section = kube_cpu_usage.parse_kube_cpu_resources_v1(resources_string_table)
    assert resources_section.request == resources_request
    assert resources_section.limit == resources_limit


def test_discovery_returns_an_iterable_with_single_element(usage_section, resources_section):
    assert len(list(kube_cpu_usage.discovery(usage_section, resources_section))) == 1
    assert len(list(kube_cpu_usage.discovery(usage_section, None))) == 1


def test_discovery_returns_an_empty_iterable(resources_section):
    assert len(list(kube_cpu_usage.discovery(None, None))) == 0
    assert len(list(kube_cpu_usage.discovery(None, resources_section))) == 0


@pytest.mark.parametrize("usage_section", [None])
def test_check_yields_no_check_results(check_result):
    assert len(list(check_result)) == 0


def test_check_yields_check_results(check_result, usage_section, resources_section):
    assert len(list(check_result)) == 2 * len(usage_section.dict()) + 3 * len(
        resources_section.dict()
    )


def test_check_yields_results(check_result, usage_section, resources_section):
    expected = len(usage_section.dict()) + len(resources_section.dict())
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


@pytest.mark.parametrize("usage_section", [None])
def test_check_yields_no_results(check_result):
    assert len(list(check_result)) == 0


@pytest.mark.parametrize("resources_section", [None])
def test_check_yields_two_results(check_result):
    assert len(list(check_result)) == 2


@pytest.mark.parametrize("resources_section", [None])
def test_check_yields_single_result_with_summary(check_result):
    expected = [f"Usage: {USAGE:0.3f}"]
    assert [r.summary for r in check_result if isinstance(r, Result)] == expected


@pytest.mark.parametrize("resources_section", [None])
def test_check_yields_single_metric_with_value(check_result):
    expected = [USAGE]
    assert [m.value for m in check_result if isinstance(m, Metric)] == expected


def test_check_yields_multiple_results_with_summaries(
    check_result, resources_request, resources_limit
):
    expected = [
        f"Usage: {USAGE:0.3f}",
        f"Request utilization: {render.percent(USAGE / resources_request * 100)} - {USAGE:0.3f} of {resources_request:0.3f}",
        f"Limit utilization: {render.percent(USAGE / resources_limit * 100)} - {USAGE:0.3f} of {resources_limit:0.3f}",
    ]
    assert [r.summary for r in check_result if isinstance(r, Result)] == expected


def test_check_yields_multiple_metrics_with_values(
    check_result, resources_request, resources_limit
):
    expected = [
        ("kube_cpu_usage", USAGE),
        ("kube_cpu_request_utilization", USAGE / resources_request * 100),
        ("kube_cpu_request", resources_request),
        ("kube_cpu_limit_utilization", USAGE / resources_limit * 100),
        ("kube_cpu_limit", resources_limit),
    ]
    assert [(m.name, m.value) for m in check_result if isinstance(m, Metric)] == expected


@pytest.mark.parametrize(
    "resources_request, resources_limit",
    list(
        itertools.product([ExceptionalResource.unspecified], [e.value for e in ExceptionalResource])
    ),
)
def test_check_yields_multiple_results_with_summaries_exceptional_res(check_result):
    expected = [f"Usage: {USAGE:0.3f}", "Request: n/a", "Limit: n/a"]
    assert [r.summary for r in check_result if isinstance(r, Result)] == expected


@pytest.mark.parametrize(
    "resources_request, resources_limit, expected_text",
    [
        (
            ExceptionalResource.unspecified,
            ExceptionalResource.unspecified,
            "not specified for at least one container",
        )
    ],
)
def test_check_yields_results_with_details_unspecified(
    check_result, resources_request, resources_limit, expected_text
):
    expected = [
        f"Usage: {USAGE:0.3f}",
        f"Request: {expected_text}",
        f"Limit: {expected_text}",
    ]
    assert [r.details for r in check_result if isinstance(r, Result)] == expected


@pytest.mark.parametrize(
    "resources_limit, expected_text",
    [
        (
            ExceptionalResource.unspecified,
            "not specified for at least one container",
        ),
        (
            ExceptionalResource.zero,
            "set to zero for at least one container",
        ),
        (
            ExceptionalResource.zero_unspecified,
            "not specified for at least one container, set to zero for at least one container",
        ),
    ],
)
def test_check_yields_results_with_details_exceptional_limits(
    check_result, resources_request, resources_limit, expected_text
):
    expected = [
        f"Usage: {USAGE:0.3f}",
        "Request utilization: 49.54% - 0.089 of 0.180",
        f"Limit: {expected_text}",
    ]
    assert [r.details for r in check_result if isinstance(r, Result)] == expected


@pytest.mark.parametrize(
    "resources_request, resources_limit",
    list(
        itertools.product([ExceptionalResource.unspecified], [e.value for e in ExceptionalResource])
    ),
)
def test_check_yields_single_metric_with_value_exceptional_res(check_result):
    expected = [USAGE]
    assert [m.value for m in check_result if isinstance(m, Metric)] == expected


@pytest.mark.parametrize("resources_request", [0])
def test_check_yields_result_with_details_request_set_to_zero(check_result):
    expected_details = "Request: set to zero for all containers"
    assert sum(r.details == expected_details for r in check_result if isinstance(r, Result)) == 1


def test_check_all_states_ok(check_result):
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


@pytest.mark.parametrize("state", [OK, WARN, CRIT])
@pytest.mark.parametrize("params_request, params_limit", [(("ignore"), ("ignore"))])
def test_check_all_states_ok_params_ignore(check_result):
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


@pytest.mark.parametrize("state", [OK, WARN, CRIT])
@pytest.mark.parametrize(
    "params_request, params_limit, expected_states",
    [
        (
            ("abs_used", (0.01, 1.0)),
            ("abs_used", (0.01, 1.0)),
            [State.OK, State.WARN, State.WARN],
        ),
        (
            ("abs_used", (0.01, 0.01)),
            ("abs_used", (0.01, 0.01)),
            [State.OK, State.CRIT, State.CRIT],
        ),
    ],
)
def test_check_abs_levels_with_mixed(expected_states, check_result):
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states


@pytest.mark.parametrize(
    "state_request, state_limit, expected_states",
    [
        (OK, OK, [State.OK, State.OK, State.OK]),
        (OK, WARN, [State.OK, State.OK, State.WARN]),
        (OK, CRIT, [State.OK, State.OK, State.CRIT]),
        (WARN, OK, [State.OK, State.WARN, State.OK]),
        (CRIT, OK, [State.OK, State.CRIT, State.OK]),
        (WARN, WARN, [State.OK, State.WARN, State.WARN]),
        (WARN, CRIT, [State.OK, State.WARN, State.CRIT]),
        (CRIT, WARN, [State.OK, State.CRIT, State.WARN]),
        (CRIT, CRIT, [State.OK, State.CRIT, State.CRIT]),
    ],
)
def test_check_result_states_mixed(expected_states, check_result):
    assert [r.state for r in check_result if isinstance(r, Result)] == expected_states
