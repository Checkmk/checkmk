#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Optional, Tuple, Union

import pytest

from cmk.base.plugins.agent_based import kube_memory
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_memory import (
    check_kube_memory,
    DEFAULT_PARAMS,
    Memory,
    Resources,
)
from cmk.base.plugins.agent_based.utils.kube_resources import ExceptionalResource

from cmk.gui.plugins.wato.check_parameters.kube_memory import _parameter_valuespec_memory

# TODO Refactor these tests, so there functionality is not lost. Also the new test needs to below
# refactored into smaller tests.

# @pytest.fixture
# def resource_request():
#    return 4000
#
#
# @pytest.fixture
# def resource_limit():
#    return 12000
#
#
# @pytest.fixture
# def usage():
#    return 3000.0
#
#
# @pytest.fixture
# def memory_performance(usage):
#    return {"memory_usage_bytes": usage}
#
#
# @pytest.fixture
# def string_table_performance(memory_performance):
#    return [[json.dumps(memory_performance)]]
#
#
# @pytest.fixture
# def string_table_resources(resource_request, resource_limit):
#    return [[json.dumps({"limit": resource_limit, "request": resource_request})]]
#
#
# @pytest.fixture
# def string_table_unset_resources():
#    return [
#        [
#            json.dumps(
#                {
#                    "limit": ExceptionalResource.unspecified,
#                    "request": ExceptionalResource.unspecified,
#                }
#            )
#        ]
#    ]
#
#
# @pytest.fixture
# def section_resources(string_table_resources):
#    return kube_memory.parse_memory_resources(string_table_resources)
#
#
# @pytest.fixture
# def section_unset_resources(string_table_unset_resources):
#    return kube_memory.parse_memory_resources(string_table_unset_resources)
#
#
# @pytest.fixture
# def section_performance(string_table_performance):
#    return kube_memory.parse_performance_memory(string_table_performance)
#
# def test_parse_resources(string_table_resources, resource_request, resource_limit):
#    section = kube_memory.parse_memory_resources(string_table_resources)
#    assert section.request == resource_request
#    assert section.limit == resource_limit
#
#
# def test_parse_performance(string_table_performance, usage):
#    section = kube_memory.parse_performance_memory(string_table_performance)
#    assert section.memory_usage_bytes == usage
#
#
# def test_discovery_returns_an_iterable(string_table_resources, string_table_performance):
#    parsed_resources = kube_memory.parse_memory_resources(string_table_resources)
#    parse_performance = kube_memory.parse_performance_memory(string_table_performance)
#    assert list(kube_memory.discovery(parsed_resources, parse_performance))
#
#
# @pytest.fixture
# def check_result(section_resources, section_performance):
#    return kube_memory.check({}, section_resources, section_performance)
#
#
# def test_check_yields_results(check_result):
#    assert len(list(check_result)) == 7
#
#
# def test_check_metrics_count(check_result):
#    assert len([m for m in check_result if isinstance(m, Metric)]) == 4
#
#
# def test_check_usage_value(check_result, usage, resource_limit):
#    total_usage = usage
#    percentage_usage = total_usage / resource_limit * 100
#    usage_result = next(check_result)
#    assert (
#        usage_result.summary
#        == f"Usage: {render.percent(percentage_usage)} - {render.bytes(total_usage)} of {render.bytes(resource_limit)}"
#    )
#
#
# def test_check_no_limit_usage(section_performance, section_unset_resources, usage):
#    check_result = list(kube_memory.check({}, section_unset_resources, section_performance))
#    usage_result = check_result[0]
#    assert isinstance(usage_result, Result)
#    assert usage_result.summary == f"Usage: {render.bytes(usage)}"
#
#
# @pytest.fixture
# def agent_performance_section(fix_register):
#    for name, section in fix_register.agent_sections.items():
#        if str(name) == "k8s_live_memory_v1":
#            return section
#    assert False, "Should be able to find the section"
#
#
# @pytest.fixture
# def agent_resources_section(fix_register):
#    for name, section in fix_register.agent_sections.items():
#        if str(name) == "kube_memory_resources_v1":
#            return section
#    assert False, "Should be able to find the section"
#
#
# @pytest.fixture
# def check_plugin(fix_register):
#    for name, plugin in fix_register.check_plugins.items():
#        if str(name) == "kube_memory":
#            return plugin
#    assert False, "Should be able to find the plugin"


@pytest.fixture
def agent_performance_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "k8s_live_memory_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def agent_resources_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "kube_memory_resources_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "kube_memory":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_memory_section_calls(agent_performance_section):
    assert str(agent_performance_section.name) == "k8s_live_memory_v1"
    assert str(agent_performance_section.parsed_section_name) == "k8s_live_memory"
    assert agent_performance_section.parse_function == kube_memory.parse_performance_memory


def test_register_agent_memory_resources_section_calls(agent_resources_section):
    assert str(agent_resources_section.name) == "kube_memory_resources_v1"
    assert str(agent_resources_section.parsed_section_name) == "kube_memory_resources"
    assert agent_resources_section.parse_function == kube_memory.parse_memory_resources


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_memory"
    assert check_plugin.service_name == "Container memory"
    assert check_plugin.discovery_function.__wrapped__ == kube_memory.discovery_kube_memory
    assert check_plugin.check_function.__wrapped__ == kube_memory.check_kube_memory


@pytest.mark.parametrize(
    "section_kube_memory_resources,section_k8s_live_memory,expected_result",
    [
        pytest.param(
            None,
            None,
            tuple(),
            id="No data",
        ),
        pytest.param(
            Resources(request=0.0, limit=28120704.0),
            None,
            tuple(),
            id="No performance data",
        ),
        pytest.param(
            None,
            Memory(memory_usage_bytes=18120704.0),
            tuple(),
            id="No resources",
        ),
        pytest.param(
            Resources(request=0.0, limit=ExceptionalResource.zero),
            Memory(memory_usage_bytes=18120704.0),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0),
                Result(
                    state=State.OK,
                    summary="Request: n/a",
                    details="Request: set to zero for all containers",
                ),
                Result(
                    state=State.OK,
                    summary="Limit: n/a",
                    details="Limit: set to zero for at least one container",
                ),
            ),
            id="Weird config data set to zero",
        ),
        pytest.param(
            Resources(
                request=ExceptionalResource.unspecified,
                limit=ExceptionalResource.unspecified,
            ),
            Memory(memory_usage_bytes=18120704.0),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0),
                Result(
                    state=State.OK,
                    summary="Request: n/a",
                    details="Request: not specified for at least one container",
                ),
                Result(
                    state=State.OK,
                    summary="Limit: n/a",
                    details="Limit: not specified for at least one container",
                ),
            ),
            id="Config data not defined for at least container",
        ),
        pytest.param(
            Resources(
                request=0.0,
                limit=ExceptionalResource.zero_unspecified,
            ),
            Memory(memory_usage_bytes=18120704.0),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0),
                Result(
                    state=State.OK,
                    summary="Request: n/a",
                    details="Request: set to zero for all containers",
                ),
                Result(
                    state=State.OK,
                    summary="Limit: n/a",
                    details="Limit: not specified for at least one container, set to zero for at least one container",
                ),
            ),
            id="Config data not defined, and limit value is zero",
        ),
        pytest.param(
            Resources(request=13120704.0, limit=28120704.0),
            Memory(memory_usage_bytes=18120704.0),
            (
                Result(state=State.OK, summary="Usage: 17.3 MiB"),
                Metric("kube_memory_usage", 18120704.0),
                Result(
                    state=State.OK, summary="Request utilization: 138.11% - 17.3 MiB of 12.5 MiB"
                ),
                Metric(
                    "kube_memory_request_utilization", 138.10771129354035, boundaries=(0.0, None)
                ),
                Metric("kube_memory_request", 13120704.0),
                Result(state=State.OK, summary="Limit utilization: 64.44% - 17.3 MiB of 26.8 MiB"),
                Metric(
                    "kube_memory_limit_utilization",
                    64.4390126221591,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_limit", 28120704.0),
            ),
            id="All config data present, usage below request, this is the desirable state for a cluster",
        ),
        pytest.param(
            Resources(request=13120704.0, limit=28120704.0),
            Memory(memory_usage_bytes=27120704.0),
            (
                Result(state=State.OK, summary="Usage: 25.9 MiB"),
                Metric("kube_memory_usage", 27120704.0),
                Result(
                    state=State.OK, summary="Request utilization: 206.70% - 25.9 MiB of 12.5 MiB"
                ),
                Metric(
                    "kube_memory_request_utilization", 206.70159162191297, boundaries=(0.0, None)
                ),
                Metric("kube_memory_request", 13120704.0),
                Result(
                    state=State.CRIT,
                    summary="Limit utilization: 96.44% - 25.9 MiB of 26.8 MiB (warn/crit at 80.00%/90.00%)",
                ),
                Metric(
                    "kube_memory_limit_utilization",
                    96.44390126221592,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, None),
                ),
                Metric("kube_memory_limit", 28120704.0),
            ),
            id="All config data present, usage above request",
        ),
    ],
)
def test_check_kube_memory(
    section_kube_memory_resources: Optional[Resources],
    section_k8s_live_memory: Optional[Memory],
    expected_result: Tuple[Union[Result, Metric], ...],
) -> None:
    assert expected_result == tuple(
        check_kube_memory(DEFAULT_PARAMS, section_kube_memory_resources, section_k8s_live_memory)
    )


def test_valuespec_and_check_agree() -> None:
    assert tuple(DEFAULT_PARAMS) == tuple(
        element[0] for element in _parameter_valuespec_memory()._get_elements()
    )
