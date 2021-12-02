#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest

from cmk.base.plugins.agent_based import kube_cpu_load
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture
def limit():
    return 0.3


@pytest.fixture
def requests():
    return 0.15


@pytest.fixture
def string_table_element(limit, requests):
    return {"limit": limit, "requests": requests}


@pytest.fixture
def string_table(string_table_element):
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    return kube_cpu_load.parse(string_table)


@pytest.fixture
def agent_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "kube_cpu_resources_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "kube_cpu_resources":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_section_calls(agent_section):
    assert str(agent_section.name) == "kube_cpu_resources_v1"
    assert str(agent_section.parsed_section_name) == "kube_cpu_resources"
    assert agent_section.parse_function == kube_cpu_load.parse


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_cpu_resources"
    assert check_plugin.service_name == "CPU Load"
    assert check_plugin.discovery_function.__wrapped__ == kube_cpu_load.discovery
    assert check_plugin.check_function.__wrapped__ == kube_cpu_load.check
    assert check_plugin.check_default_parameters == {}


def test_parse(string_table, limit, requests):
    section = kube_cpu_load.parse(string_table)
    assert section.limit == limit
    assert section.requests == requests


def test_discovery_returns_an_iterable(string_table):
    parsed = kube_cpu_load.parse(string_table)
    assert list(kube_cpu_load.discovery(parsed))


@pytest.fixture
def check_result(section):
    return kube_cpu_load.check({}, section)


def test_check_yields_check_results(check_result, section):
    assert len(list(check_result)) == len(section.dict())


def test_check_yields_results(check_result, section):
    expected = len(section.dict())
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


def test_check_all_states_ok(check_result):
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


def test_check_calls_results_with_summary(check_result, section):
    expected_summaries = [f"{key.title()}: {val}" for key, val in section.dict().items()]
    actual_summaries = [r.summary for r in check_result]
    assert actual_summaries == expected_summaries
