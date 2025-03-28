#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping
from unittest.mock import MagicMock

import pytest

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    CheckPlugin,
)

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based import kube_node_container_count
from cmk.plugins.kube.schemata.section import ContainerCount


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
def agent_section(agent_based_plugins: AgentBasedPlugins) -> AgentSectionPlugin:
    for name, section in agent_based_plugins.agent_sections.items():
        if str(name) == "kube_node_container_count_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    for name, plugin in agent_based_plugins.check_plugins.items():
        if str(name) == "kube_node_container_count":
            return plugin
    assert False, "Should be able to find the plugin"


def test_register_agent_section_calls(agent_section: AgentSectionPlugin) -> None:
    assert str(agent_section.name) == "kube_node_container_count_v1"
    assert str(agent_section.parsed_section_name) == "kube_node_container_count"
    assert agent_section.parse_function == kube_node_container_count.parse


def test_register_check_plugin_calls(check_plugin) -> None:  # type: ignore[no-untyped-def]
    assert str(check_plugin.name) == "kube_node_container_count"
    assert check_plugin.service_name == "Containers"
    assert check_plugin.discovery_function.__wrapped__ == kube_node_container_count.discovery
    assert check_plugin.check_function.__wrapped__ == kube_node_container_count.check
    assert check_plugin.check_default_parameters == {}
    assert str(check_plugin.check_ruleset_name) == "kube_node_container_count"


def test_parse(string_table: StringTable, running: int, waiting: int, terminated: int) -> None:
    section = kube_node_container_count.parse(string_table)
    assert section.running == running
    assert section.waiting == waiting
    assert section.terminated == terminated


def test_discovery_returns_an_iterable(string_table: StringTable) -> None:
    parsed = kube_node_container_count.parse(string_table)
    assert list(kube_node_container_count.discovery(parsed))


@pytest.fixture
def params():
    return {
        "running_upper": ("levels", (10, 15)),
        "running_lower": ("levels", (5, 2)),
        "waiting_upper": ("levels", (2, 5)),
        "waiting_lower": ("levels", (0, 0)),
        "terminated_upper": ("levels", (1, 1)),
        "terminated_lower": ("levels", (0, 0)),
        "total_upper": ("levels", (10, 15)),
        "total_lower": ("levels", (0, 0)),
    }


@pytest.fixture
def check_result(section, params):
    return kube_node_container_count.check(params, section)


def test_check_yields_check_results(check_result: CheckResult, section: ContainerCount) -> None:
    assert len(list(check_result)) == 2 * len(section.model_dump()) + 2


def test_check_yields_results(check_result: CheckResult, section: ContainerCount) -> None:
    expected = len(section.model_dump()) + 1
    assert len([r for r in check_result if isinstance(r, Result)]) == expected


def test_check_all_states_ok(check_result: CheckResult) -> None:
    assert all(r.state == State.OK for r in check_result if isinstance(r, Result))


def test_check_yields_metrics(check_result: CheckResult, section: ContainerCount) -> None:
    expected = len(section.model_dump()) + 1
    assert len([m for m in check_result if isinstance(m, Metric)]) == expected


def test_check_all_metrics_values(check_result: CheckResult, section: ContainerCount) -> None:
    expected = [*section.model_dump().values(), sum(section.model_dump().values())]
    assert [m.value for m in check_result if isinstance(m, Metric)] == expected


@pytest.fixture
def check_levels(mocker, autouse=True):
    return mocker.spy(kube_node_container_count, "check_levels_v1")


def test_check_issues_expected_check_levels_calls(
    check_levels: MagicMock, check_result: CheckResult, section: ContainerCount
) -> None:
    list(check_result)
    assert check_levels.call_count == len(section.model_dump()) + 1


def test_check_calls_check_levels_with_values(
    check_levels: MagicMock, check_result: CheckResult, section: ContainerCount
) -> None:
    expected_values = [*section.model_dump().values(), sum(section.model_dump().values())]
    list(check_result)
    actual_values = [call.args[0] for call in check_levels.call_args_list]
    assert actual_values == expected_values


def test_check_calls_check_levels_with_levels_from_params(
    check_levels: MagicMock, check_result: CheckResult, params: Mapping[str, tuple[str, object]]
) -> None:
    list(check_result)
    actual_levels = []
    for call in check_levels.call_args_list:
        actual_levels.append(("levels", call.kwargs["levels_upper"]))
        actual_levels.append(("levels", call.kwargs["levels_lower"]))
    assert actual_levels == list(params.values())


@pytest.mark.parametrize("params", [{}])
def test_check_calls_check_levels_with_levels_default(
    check_levels: MagicMock, check_result: CheckResult
) -> None:
    list(check_result)
    assert all(call.kwargs["levels_upper"] is None for call in check_levels.call_args_list)
    assert all(call.kwargs["levels_lower"] is None for call in check_levels.call_args_list)


def test_check_calls_check_levels_with_metric_name(
    check_levels: MagicMock, check_result: CheckResult, section: ContainerCount
) -> None:
    expected_metrics = [
        f"kube_node_container_count_{name}" for name in [*section.model_dump(), "total"]
    ]
    list(check_result)
    actual_metrics = [call.kwargs["metric_name"] for call in check_levels.call_args_list]
    assert actual_metrics == expected_metrics


def test_check_calls_check_levels_with_labels(
    check_levels: MagicMock, check_result: CheckResult, section: ContainerCount
) -> None:
    expected_labels = [f"{name.title()}" for name in [*section.model_dump(), "total"]]
    list(check_result)
    actual_labels = [call.kwargs["label"] for call in check_levels.call_args_list]
    assert actual_labels == expected_labels
