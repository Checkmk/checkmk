#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

# import itertools
import json

import pytest

from cmk.base.plugins.agent_based import kube_cpu_usage

# from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, render, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result


@pytest.fixture
def usage_usage():
    return 0.089179359719143728735745


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
def resources_limit():
    return 0.3


@pytest.fixture
def resources_request():
    return 0.15


@pytest.fixture
def resources_string_table_element(resources_limit, resources_request):
    return {"limit": resources_limit, "request": resources_request}


@pytest.fixture
def resources_string_table(resources_string_table_element):
    return [[json.dumps(resources_string_table_element)]]


@pytest.fixture
def resources_section(resources_string_table):
    return kube_cpu_usage.parse_kube_cpu_resources_v1(resources_string_table)


@pytest.fixture
def check_result(usage_section, resources_section):
    return kube_cpu_usage.check(
        kube_cpu_usage.Params(request="ignore", limit=("perc_used", (80.0, 90.0))),
        usage_section,
        resources_section,
    )


@pytest.fixture
def agent_section(fix_register):
    for name, resources_section in fix_register.agent_sections.items():
        if str(name) == "kube_cpu_resources_v1":
            return resources_section
    assert False, "Should be able to find the resources_section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "kube_cpu_usage":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_section_calls(agent_section):
    assert str(agent_section.name) == "kube_cpu_resources_v1"
    assert str(agent_section.parsed_section_name) == "kube_cpu_resources"
    assert agent_section.parse_function == kube_cpu_usage.parse_kube_cpu_resources_v1


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_cpu_usage"
    assert check_plugin.service_name == "Container CPU"
    assert check_plugin.discovery_function.__wrapped__ == kube_cpu_usage.discovery
    assert check_plugin.check_function.__wrapped__ == kube_cpu_usage.check


def test_parse_kube_cpu_resources_v1(resources_string_table, resources_limit, resources_request):
    resources_section = kube_cpu_usage.parse_kube_cpu_resources_v1(resources_string_table)
    assert resources_section.limit == resources_limit
    assert resources_section.request == resources_request


def test_discovery_returns_an_iterable_with_one_element(usage_section, resources_section):
    assert len(list(kube_cpu_usage.discovery(usage_section, resources_section))) == 1
    assert len(list(kube_cpu_usage.discovery(usage_section, None))) == 1


# def test_discovery_returns_an_empty_iterable(resources_section):
#     assert len(list(kube_cpu_usage.discovery(None, None))) == 0
#     assert len(list(kube_cpu_usage.discovery(None, resources_section))) == 0


@pytest.mark.parametrize("usage_section", [None])
def test_check_yields_no_check_results(check_result):
    assert len(list(check_result)) == 0


# def test_check_yields_check_results(check_result, usage_section, resources_section):
#     assert len(list(check_result)) == len(usage_section.dict()) + 2 * len(resources_section.dict())


def test_check_yields_results(check_result, usage_section, resources_section):
    expected = len(usage_section.dict()) + len(resources_section.dict())
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


@pytest.mark.parametrize("usage_section", [None])
def test_check_yields_no_results(check_result):
    assert len(list(check_result)) == 0


# @pytest.mark.parametrize("resources_section", [None])
# def test_check_yields_one_results(check_result):
#     assert len(list(check_result)) == 1


# @pytest.mark.parametrize("resources_section", [None])
# def test_check_yields_one_result_with_summary(check_result, usage_usage):
#     expected = [f"CPU usage: {usage_usage:0.3f}"]
#     assert [r.summary for r in check_result] == expected


# def test_check_yields_one_result_with_summaries(
#     check_result, usage_usage, resources_limit, resources_request
# ):
#     expected = [
#         f"CPU usage: {usage_usage:0.3f}",
#         f"Limit utilization: {render.percent(usage_usage / resources_limit * 100)} - {usage_usage:0.3f} of {resources_limit:0.3f}",
#         f"Request utilization: {render.percent(usage_usage / resources_request * 100)} - {usage_usage:0.3f} of {resources_request:0.3f} (warn/crit at 50.00%/80.00%)",
#     ]
#     assert [r.summary for r in check_result if isinstance(r, Result)] == expected


# def test_check_yields_one_result_with_metric_values(
#     check_result, usage_usage, resources_limit, resources_request
# ):
#     expected = [
#         ("limit_utilization", usage_usage / resources_limit * 100),
#         ("request_utilization", usage_usage / resources_request * 100),
#     ]
#     assert [(m.name, m.value) for m in check_result if isinstance(m, Metric)] == expected


# @pytest.mark.parametrize(
#     "resources_limit, resources_request",
#     list(
#         itertools.product(["unspecified", "zero", "zero_unspecified"], ["unspecified"])
#     ),  # FIXME: remove hardcoded values
# )
# def test_check_yields_one_result_with_summaries_aggregated_results(check_result, usage_usage):
#     expected = [f"CPU usage: {usage_usage:0.3f}", "Limit n/a", "Request n/a"]
#     assert [r.summary for r in check_result] == expected


# @pytest.mark.parametrize(
#     "resources_limit, resources_request",
#     list(
#         itertools.product(["unspecified", "zero", "zero_unspecified"], ["unspecified"])
#     ),  # FIXME: remove hardcoded values
# )
# def test_check_yields_one_results_with_details_aggregated_results(
#     check_result, usage_usage, resources_limit, resources_request
# ):
#     expected = [
#         f"CPU usage: {usage_usage:0.3f}",
#         f"Limit: {resources_limit}",
#         f"Request: {resources_request}",
#     ]
#     assert [r.details for r in check_result] == expected


# def test_check_all_states_ok(check_result):
#     expected = [State.OK, State.OK, State.WARN]
#     assert [r.state for r in check_result if isinstance(r, Result)] == expected
