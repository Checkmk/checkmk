#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest

from cmk.base.api.agent_based.checking_classes import Metric
from cmk.base.plugins.agent_based import k8s_memory
from cmk.base.plugins.agent_based.agent_based_api.v1 import render, Result


@pytest.fixture
def requests():
    return 4000


@pytest.fixture
def limit():
    return 12000


@pytest.fixture
def usage():
    return 3000


@pytest.fixture
def container_count():
    return 2


@pytest.fixture
def memory_performance(usage):
    return {
        "memory_usage": usage,
        "memory_swap": 0,
    }


@pytest.fixture
def string_table_performance(container_count, memory_performance):
    return [[json.dumps({str(i): memory_performance for i in range(container_count)})]]


@pytest.fixture
def string_table_resources(requests, limit):
    return [[json.dumps({"limit": limit, "requests": requests})]]


@pytest.fixture
def string_table_unset_resources():
    return [[json.dumps({"limit": float("inf"), "requests": float("inf")})]]


@pytest.fixture
def section_resources(string_table_resources):
    return k8s_memory.parse_memory_resources(string_table_resources)


@pytest.fixture
def section_unset_resources(string_table_unset_resources):
    return k8s_memory.parse_memory_resources(string_table_unset_resources)


@pytest.fixture
def section_performance(string_table_performance):
    return k8s_memory.parse_performance_memory(string_table_performance)


@pytest.fixture
def agent_performance_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "k8s_live_memory_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def agent_resources_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "k8s_memory_resources_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "k8s_memory":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_memory_section_calls(agent_performance_section):
    assert str(agent_performance_section.name) == "k8s_live_memory_v1"
    assert str(agent_performance_section.parsed_section_name) == "k8s_live_memory"
    assert agent_performance_section.parse_function == k8s_memory.parse_performance_memory


def test_register_agent_memory_resources_section_calls(agent_resources_section):
    assert str(agent_resources_section.name) == "k8s_memory_resources_v1"
    assert str(agent_resources_section.parsed_section_name) == "k8s_memory_resources"
    assert agent_resources_section.parse_function == k8s_memory.parse_memory_resources


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "k8s_memory"
    assert check_plugin.service_name == "Memory"
    assert check_plugin.discovery_function.__wrapped__ == k8s_memory.discovery
    assert check_plugin.check_function.__wrapped__ == k8s_memory.check


def test_parse_resources(string_table_resources, requests, limit):
    section = k8s_memory.parse_memory_resources(string_table_resources)
    assert section.requests == requests
    assert section.limit == limit


def test_parse_performance(string_table_performance, usage):
    section = k8s_memory.parse_performance_memory(string_table_performance)
    for _container_name, metrics in section.items():
        assert metrics.memory_usage == usage


def test_discovery_returns_an_iterable(string_table_resources, string_table_performance):
    parsed_resources = k8s_memory.parse_memory_resources(string_table_resources)
    parse_performance = k8s_memory.parse_performance_memory(string_table_performance)
    assert list(k8s_memory.discovery(parsed_resources, parse_performance))


@pytest.fixture
def check_result(section_resources, section_performance):
    return k8s_memory.check({}, section_resources, section_performance)


def test_check_yields_results(check_result):
    assert len(list(check_result)) == 7


def test_check_metrics_count(check_result):
    assert len([m for m in check_result if isinstance(m, Metric)]) == 4


def test_check_usage_value(check_result, usage, limit, container_count):
    total_usage = container_count * usage
    percentage_usage = total_usage / limit * 100
    usage_result = next(check_result)
    assert (
        usage_result.summary
        == f"Usage: {render.percent(percentage_usage)} - {render.bytes(total_usage)} of {render.bytes(limit)}"
    )


def test_check_no_limit_usage(section_performance, section_unset_resources, usage, container_count):
    check_result = list(k8s_memory.check({}, section_unset_resources, section_performance))
    usage_result = check_result[0]
    assert isinstance(usage_result, Result)
    assert usage_result.summary == f"Usage: {render.bytes(container_count*usage)}"
