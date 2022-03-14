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
    AllocatableResource,
    check_kube_memory,
    DEFAULT_PARAMS,
    Params,
    Resources,
)
from cmk.base.plugins.agent_based.utils.k8s import Memory, PerformanceUsage

from cmk.gui.plugins.wato.check_parameters.kube_resources import _parameter_valuespec_memory

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


@pytest.fixture
def agent_performance_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "kube_performance_memory_v1":
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


@pytest.fixture
def section_kube_memory_allocatable_resource():
    return AllocatableResource(context="node", value=35917989.0)


def test_register_agent_memory_section_calls(agent_performance_section):
    assert str(agent_performance_section.name) == "kube_performance_memory_v1"
    assert str(agent_performance_section.parsed_section_name) == "kube_performance_memory"
    assert agent_performance_section.parse_function == kube_memory.parse_performance_usage


def test_register_agent_memory_resources_section_calls(agent_resources_section):
    assert str(agent_resources_section.name) == "kube_memory_resources_v1"
    assert str(agent_resources_section.parsed_section_name) == "kube_memory_resources"
    assert agent_resources_section.parse_function == kube_memory.parse_resources


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_memory"
    assert check_plugin.service_name == "Memory resources"
    assert check_plugin.discovery_function.__wrapped__ == kube_memory.discovery_kube_memory
    assert check_plugin.check_function.__wrapped__ == kube_memory.check_kube_memory


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
                count_total=2,
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
                count_total=2,
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
                count_total=2,
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
                count_total=3,
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
                count_total=2,
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
                count_total=2,
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
    section_kube_performance_memory: Optional[PerformanceUsage],
    section_kube_memory_resources: Optional[Resources],
    section_kube_memory_allocatable_resource: Optional[AllocatableResource],
    expected_result: Tuple[Union[Result, Metric], ...],
) -> None:
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
def test_crashes_if_no_resources(section_kube_performance_memory) -> None:
    with pytest.raises(AssertionError):
        list(
            check_kube_memory(
                DEFAULT_PARAMS,
                section_kube_performance_memory,
                None,
                AllocatableResource(context="node", value=35917989.0),
            )
        )


def test_valuespec_and_check_agree() -> None:
    assert tuple(DEFAULT_PARAMS) == tuple(
        element[0] for element in _parameter_valuespec_memory()._get_elements()
    )
