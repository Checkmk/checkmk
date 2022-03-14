#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest

from cmk.base.api.agent_based.checking_classes import Metric
from cmk.base.plugins.agent_based import kube_node_container_count
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture
def running():
    return 8


@pytest.fixture
def waiting():
    return 1


@pytest.fixture
def terminated():
    return 0


@pytest.fixture
def string_table(running, waiting, terminated):
    return [[json.dumps({"running": running, "waiting": waiting, "terminated": terminated})]]


@pytest.fixture
def section(string_table):
    return kube_node_container_count.parse(string_table)


@pytest.fixture
def agent_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "kube_node_container_count_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "kube_node_container_count":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_section_calls(agent_section):
    assert str(agent_section.name) == "kube_node_container_count_v1"
    assert str(agent_section.parsed_section_name) == "kube_node_container_count"
    assert agent_section.parse_function == kube_node_container_count.parse


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_node_container_count"
    assert check_plugin.service_name == "Containers"
    assert check_plugin.discovery_function.__wrapped__ == kube_node_container_count.discovery
    assert check_plugin.check_function.__wrapped__ == kube_node_container_count.check
    assert check_plugin.check_default_parameters == {}
    assert str(check_plugin.check_ruleset_name) == "kube_node_container_count"


def test_parse(string_table, running, waiting, terminated):
    section = kube_node_container_count.parse(string_table)
    assert section.running == running
    assert section.waiting == waiting
    assert section.terminated == terminated


def test_discovery_returns_an_iterable(string_table):
    parsed = kube_node_container_count.parse(string_table)
    assert list(kube_node_container_count.discovery(parsed))


@pytest.fixture
def params():
    return {
        "running_upper": (10, 15),
        "running_lower": (5, 2),
        "waiting_upper": (2, 5),
        "waiting_lower": (0, 0),
        "terminated_upper": (1, 1),
        "terminated_lower": (0, 0),
        "total_upper": (10, 15),
        "total_lower": (0, 0),
    }


@pytest.fixture
def check_result(section, params):
    return kube_node_container_count.check(params, section)


def test_check_yields_check_results(check_result, section):
    assert len(list(check_result)) == 2 * len(section.dict()) + 2


def test_check_yields_results(check_result, section):
    expected = len(section.dict()) + 1
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


def test_check_all_states_ok(check_result):
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


def test_check_yields_metrics(check_result, section):
    expected = len(section.dict()) + 1
    assert len([m for m in check_result if isinstance(m, Metric)]) == expected


def test_check_all_metrics_values(check_result, section):
    expected = [*section.dict().values(), sum(section.dict().values())]
    assert [m.value for m in check_result if isinstance(m, Metric)] == expected


@pytest.fixture
def check_levels(mocker, autouse=True):
    return mocker.spy(kube_node_container_count, "check_levels")


def test_check_issues_expected_check_levels_calls(check_levels, check_result, section):
    list(check_result)
    assert check_levels.call_count == len(section.dict()) + 1


def test_check_calls_check_levels_with_values(check_levels, check_result, section):
    expected_values = [*section.dict().values(), sum(section.dict().values())]
    list(check_result)
    actual_values = [call.args[0] for call in check_levels.call_args_list]
    assert actual_values == expected_values


def test_check_calls_check_levels_with_levels_from_params(check_levels, check_result, params):
    list(check_result)
    actual_levels = []
    for call in check_levels.call_args_list:
        actual_levels.extend([call.kwargs["levels_upper"], call.kwargs["levels_lower"]])
    assert actual_levels == list(params.values())


@pytest.mark.parametrize("params", [{}])
def test_check_calls_check_levels_with_levels_default(check_levels, check_result):
    list(check_result)
    assert all(call.kwargs["levels_upper"] is None for call in check_levels.call_args_list)
    assert all(call.kwargs["levels_lower"] is None for call in check_levels.call_args_list)


def test_check_calls_check_levels_with_metric_name(check_levels, check_result, section):
    expected_metrics = [f"kube_node_container_count_{name}" for name in [*section.dict(), "total"]]
    list(check_result)
    actual_metrics = [call.kwargs["metric_name"] for call in check_levels.call_args_list]
    assert actual_metrics == expected_metrics


def test_check_calls_check_levels_with_labels(check_levels, check_result, section):
    expected_labels = [f"{name.title()}" for name in [*section.dict(), "total"]]
    list(check_result)
    actual_labels = [call.kwargs["label"] for call in check_levels.call_args_list]
    assert actual_labels == expected_labels
