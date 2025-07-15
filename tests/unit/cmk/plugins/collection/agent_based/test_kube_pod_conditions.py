#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import ValidationError

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    CheckPlugin,
)

from cmk.agent_based.v2 import CheckResult, render, Result, State, StringTable
from cmk.plugins.collection.agent_based import kube_pod_conditions
from cmk.plugins.kube.schemata.section import PodCondition, PodConditions

MINUTE = 60
TIMESTAMP = 359

OK = 0
WARN = 3
CRIT = 5

RECENT = {"timestamp": TIMESTAMP - OK * MINUTE}
STALE_WARN = {"timestamp": TIMESTAMP - WARN * MINUTE}
STALE_CRIT = {"timestamp": TIMESTAMP - CRIT * MINUTE}

REASON = "MuchReason"
DETAIL = "wow detail many detailed"


class PodConditionsFactory(ModelFactory):
    __model__ = PodConditions

    disruptiontarget = None


class PodConditionFactory(ModelFactory):
    __model__ = PodCondition

    last_transition_time = TIMESTAMP


def ready(time_diff_minutes=0):
    return {
        "status": True,
        "reason": None,
        "detail": None,
        "last_transition_time": TIMESTAMP - time_diff_minutes * MINUTE,
    }


def not_ready(time_diff_minutes=0):
    return {
        "status": False,
        "reason": REASON,
        "detail": DETAIL,
        "last_transition_time": TIMESTAMP - time_diff_minutes * MINUTE,
    }


@pytest.fixture
def state():
    return OK


@pytest.fixture
def state_initialized(state):
    return state


@pytest.fixture
def state_scheduled(state):
    return state


@pytest.fixture
def state_containersready(state):
    return state


@pytest.fixture
def state_ready(state):
    return state


@pytest.fixture
def status():
    return True


@pytest.fixture
def status_initialized(status):
    return status


@pytest.fixture
def status_scheduled(status):
    return status


@pytest.fixture
def status_containersready(status):
    return status


@pytest.fixture
def status_ready(status):
    return status


@pytest.fixture
def string_table_element(
    status_initialized,
    status_scheduled,
    status_containersready,
    status_ready,
    state_initialized,
    state_scheduled,
    state_containersready,
    state_ready,
):
    return {
        "initialized": (
            ready(state_initialized)
            if status_initialized
            else (not_ready(state_initialized) if status_initialized is False else None)
        ),
        "hasnetwork": ready(True),
        "scheduled": (
            ready(state_scheduled)
            if status_scheduled
            else (not_ready(state_scheduled) if status_scheduled is False else None)
        ),
        "containersready": (
            ready(state_containersready)
            if status_containersready
            else (not_ready(state_containersready) if status_containersready is False else None)
        ),
        "ready": (
            ready(state_ready)
            if status_ready
            else (not_ready(state_ready) if status_ready is False else None)
        ),
    }


@pytest.fixture
def string_table(string_table_element):
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    return kube_pod_conditions.parse(string_table)


@pytest.fixture
def params():
    return {
        "initialized": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
        "scheduled": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
        "containersready": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
        "ready": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
    }


@pytest.fixture
def check_result(params, section):
    return kube_pod_conditions._check(TIMESTAMP, params, section)


@pytest.fixture
def agent_section(agent_based_plugins: AgentBasedPlugins) -> AgentSectionPlugin:
    for name, section in agent_based_plugins.agent_sections.items():
        if str(name) == "kube_pod_conditions_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    for name, plugin in agent_based_plugins.check_plugins.items():
        if str(name) == "kube_pod_conditions":
            return plugin
    assert False, "Should be able to find the plugin"


def test_parse(string_table: StringTable) -> None:
    section = kube_pod_conditions.parse(string_table)

    def assert_ready(cond: PodCondition | None) -> None:
        if cond is None:
            raise AssertionError("Condition should not be None")
        assert cond.model_dump() == ready()

    assert_ready(section.initialized)
    assert_ready(section.scheduled)
    assert_ready(section.containersready)
    assert_ready(section.ready)


@pytest.mark.parametrize(
    """
        status_initialized,
        status_scheduled,
        status_containersready,
        status_ready,
        expected_initialized,
        expected_scheduled,
        expected_containersready,
        expected_ready,
    """,
    [
        (True, True, True, True, ready(), ready(), ready(), ready()),
        (True, True, False, False, ready(), ready(), not_ready(), not_ready()),
        (None, False, None, None, None, not_ready(), None, None),
        (False, False, None, None, not_ready(), not_ready(), None, None),
        (False, False, False, False, not_ready(), not_ready(), not_ready(), not_ready()),
    ],
    ids=[
        "all_ok",
        "initialized_scheduled",
        "unscheduled",
        "unscheduled_uninitialized",
        "all_not_ok",
    ],
)
def test_parse_multi(
    expected_initialized, expected_scheduled, expected_containersready, expected_ready, string_table
):
    expected_initialized = (
        PodCondition(**expected_initialized) if expected_initialized is not None else None
    )
    expected_scheduled = PodCondition(**expected_scheduled)
    expected_containersready = (
        PodCondition(**expected_containersready) if expected_containersready is not None else None
    )
    expected_ready = PodCondition(**expected_ready) if expected_ready is not None else None
    section = kube_pod_conditions.parse(string_table)
    assert section.initialized == expected_initialized
    assert section.scheduled == expected_scheduled
    assert section.containersready == expected_containersready
    assert section.ready == expected_ready


@pytest.mark.parametrize("state", [CRIT])
@pytest.mark.parametrize(
    "status_initialized, status_scheduled, status_containersready, status_ready",
    [(None, None, None, None)],
)
def test_parse_fails_when_all_conditions_empty(string_table: StringTable) -> None:
    with pytest.raises(ValidationError):
        kube_pod_conditions.parse(string_table)


def test_discovery_returns_an_iterable(string_table: StringTable) -> None:
    parsed = kube_pod_conditions.parse(string_table)
    assert list(kube_pod_conditions.discovery(parsed))


@pytest.mark.parametrize("status", [True, False])
def test_check_all_states_ok(check_result: CheckResult) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


def test_check_all_results_with_summary_status_false():
    condition_status = False
    section = PodConditionsFactory.build(
        initialized=PodConditionFactory.build(
            status=condition_status, reason=REASON, detail=DETAIL
        ),
        hasnetwork=PodConditionFactory.build(status=condition_status, reason=REASON, detail=DETAIL),
        scheduled=PodConditionFactory.build(status=condition_status, reason=REASON, detail=DETAIL),
        containersready=PodConditionFactory.build(
            status=condition_status, reason=REASON, detail=DETAIL
        ),
        ready=PodConditionFactory.build(status=condition_status, reason=REASON, detail=DETAIL),
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    expected_summaries = [
        f"{k.upper()}: False ({REASON}: {DETAIL}) for 0 seconds"
        for k in ["scheduled", "hasnetwork", "initialized", "containersready", "ready"]
    ]
    assert list(r.summary for r in check_result if isinstance(r, Result)) == expected_summaries


@pytest.mark.parametrize("status", [True])
@pytest.mark.parametrize("state", [0, WARN, CRIT])
def test_check_results_state_ok_when_status_true(
    check_result: CheckResult,
) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize(
    "params",
    [
        {
            "scheduled": "no_levels",
            "initialized": "no_levels",
            "containersready": "no_levels",
            "ready": "no_levels",
        }
    ],
)
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_results_state_ok_when_status_false_and_no_levels(
    check_result: CheckResult,
) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize("params", [{}])
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_results_state_ok_when_status_false_and_no_params(
    check_result: CheckResult,
) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


def test_check_results_sets_summary_when_status_false(
    state: float, check_result: CheckResult
) -> None:
    condition_status = False
    transition_timestamp = TIMESTAMP - state * MINUTE
    pod_condition_with_false_status = PodConditionFactory.build(
        status=condition_status,
        last_transition_time=transition_timestamp,
        reason=REASON,
        detail=DETAIL,
    )
    section = PodConditionsFactory.build(
        initialized=pod_condition_with_false_status,
        hasnetwork=pod_condition_with_false_status,
        scheduled=pod_condition_with_false_status,
        containersready=pod_condition_with_false_status,
        ready=pod_condition_with_false_status,
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    time_diff = render.timespan(TIMESTAMP - transition_timestamp)
    expected_prefixes = [
        f"{k.upper()}: False ({REASON}: {DETAIL}) for {time_diff}"
        for k in [
            "scheduled",
            "hasnetwork",
            "initialized",
            "containersready",
            "ready",
            "disruptiontarget",
        ]
    ]
    for expected_prefix, result in zip(expected_prefixes, check_result):
        assert isinstance(result, Result) and result.summary.startswith(expected_prefix)


def test_register_agent_section_calls(agent_section: AgentSectionPlugin) -> None:
    assert str(agent_section.name) == "kube_pod_conditions_v1"
    assert str(agent_section.parsed_section_name) == "kube_pod_conditions"
    assert agent_section.parse_function == kube_pod_conditions.parse


def test_register_check_plugin_calls(check_plugin: CheckPlugin) -> None:
    assert str(check_plugin.name) == "kube_pod_conditions"
    assert check_plugin.service_name == "Condition"
    assert check_plugin.discovery_function.__wrapped__ == kube_pod_conditions.discovery  # type: ignore[attr-defined]
    assert check_plugin.check_function.__wrapped__ == kube_pod_conditions.check  # type: ignore[attr-defined]
    assert check_plugin.check_default_parameters == {
        "scheduled": "no_levels",
        "hasnetwork": "no_levels",
        "initialized": "no_levels",
        "containersready": "no_levels",
        "ready": "no_levels",
    }
    assert str(check_plugin.check_ruleset_name) == "kube_pod_conditions"


def test_check_disruption_target_condition():
    condition_status = True
    section = PodConditionsFactory.build(
        initialized=PodConditionFactory.build(status=condition_status),
        hasnetwork=PodConditionFactory.build(status=condition_status),
        scheduled=PodConditionFactory.build(status=condition_status),
        containersready=PodConditionFactory.build(status=condition_status),
        ready=PodConditionFactory.build(status=condition_status),
        disruptiontarget=PodConditionFactory.build(
            status=condition_status, reason="EvictionByEvictionAPI", detail="EvictionAPI: evicting"
        ),
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    assert list(r.summary for r in check_result if isinstance(r, Result)) == [
        "SCHEDULED: True",
        "HASNETWORK: True",
        "INITIALIZED: True",
        "CONTAINERSREADY: True",
        "READY: True",
        "DISRUPTIONTARGET: True (EvictionByEvictionAPI: EvictionAPI: evicting)",
    ]
