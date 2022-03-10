#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest
from pydantic import ValidationError

from cmk.base.plugins.agent_based import kube_pod_conditions
from cmk.base.plugins.agent_based.agent_based_api.v1 import render, State

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


@pytest.fixture(autouse=True)
def time(mocker):
    def time_side_effect():
        timestamp = TIMESTAMP
        while True:
            yield timestamp
            timestamp += MINUTE

    time_mock = mocker.Mock(side_effect=time_side_effect())
    mocker.patch.object(kube_pod_conditions, "time", mocker.Mock(time=time_mock))
    return time_mock


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
        "initialized": ready(state_initialized)
        if status_initialized
        else (not_ready(state_initialized) if status_initialized is False else None),
        "scheduled": ready(state_scheduled)
        if status_scheduled
        else (not_ready(state_scheduled) if status_scheduled is False else None),
        "containersready": ready(state_containersready)
        if status_containersready
        else (not_ready(state_containersready) if status_containersready is False else None),
        "ready": ready(state_ready)
        if status_ready
        else (not_ready(state_ready) if status_ready is False else None),
    }


@pytest.fixture
def string_table(string_table_element):
    return [[json.dumps(string_table_element)]]


@pytest.fixture
def section(string_table):
    return kube_pod_conditions.parse(string_table)


@pytest.fixture
def params():
    return dict(
        initialized=("levels", (WARN * MINUTE, CRIT * MINUTE)),
        scheduled=("levels", (WARN * MINUTE, CRIT * MINUTE)),
        containersready=("levels", (WARN * MINUTE, CRIT * MINUTE)),
        ready=("levels", (WARN * MINUTE, CRIT * MINUTE)),
    )


@pytest.fixture
def check_result(params, section):
    return kube_pod_conditions.check(params, section)


@pytest.fixture
def agent_section(fix_register):
    for name, section in fix_register.agent_sections.items():
        if str(name) == "kube_pod_conditions_v1":
            return section
    assert False, "Should be able to find the section"


@pytest.fixture
def check_plugin(fix_register):
    for name, plugin in fix_register.check_plugins.items():
        if str(name) == "kube_pod_conditions":
            return plugin
    assert False, "Should be able to find the plugin"


def test_parse(string_table):
    section = kube_pod_conditions.parse(string_table)
    assert section.initialized == ready()
    assert section.scheduled == ready()
    assert section.containersready == ready()
    assert section.ready == ready()


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
def test_parse_fails_when_all_conditions_empty(string_table):
    with pytest.raises(ValidationError):
        kube_pod_conditions.parse(string_table)


def test_discovery_returns_an_iterable(string_table):
    parsed = kube_pod_conditions.parse(string_table)
    assert list(kube_pod_conditions.discovery(parsed))


@pytest.mark.parametrize(
    "status, expected_length", [(True, 1), (False, len(kube_pod_conditions.LOGICAL_ORDER))]
)
def test_check_yields_check_results(check_result, expected_length):
    assert len(list(check_result)) == expected_length


@pytest.mark.parametrize("status", [True, False])
def test_check_all_states_ok(check_result):
    assert all(r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [True])
def test_check_all_results_with_summary_status_true(status, check_result, section):
    assert list(r.summary for r in check_result) == ["Ready, all conditions passed"]


@pytest.mark.parametrize("status", [False])
def test_check_all_results_with_summary_status_false(status, check_result, section):
    expected_summaries = [
        f"{k.upper()}: {status} ({REASON}: {DETAIL}) for 0 seconds"
        for k in kube_pod_conditions.LOGICAL_ORDER
    ]
    assert list(r.summary for r in check_result) == expected_summaries


@pytest.mark.parametrize("status", [True])
@pytest.mark.parametrize("state", [0, WARN, CRIT])
def test_check_results_state_ok_when_status_true(check_result):
    assert all(r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize(
    "state, expected_state",
    [(OK, State.OK), (WARN, State.WARN), (CRIT, State.CRIT)],
)
def test_check_results_sets_state_when_status_false(expected_state, check_result):
    assert all(r.state == expected_state for r in check_result)


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
def test_check_results_state_ok_when_status_false_and_no_levels(check_result):
    assert all(r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize("params", [{}])
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_results_state_ok_when_status_false_and_no_params(check_result):
    assert all(r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_results_sets_summary_when_status_false(state, check_result):
    time_diff = render.timespan(state * MINUTE)
    expected_prefixes = [
        f"{k.upper()}: False ({REASON}: {DETAIL}) for {time_diff}"
        for k in kube_pod_conditions.LOGICAL_ORDER
    ]
    for expected_prefix, result in zip(expected_prefixes, check_result):
        assert result.summary.startswith(expected_prefix)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize(
    """
        state_initialized,
        state_scheduled,
        state_containersready,
        state_ready,
        expected_state_initialized,
        expected_state_scheduled,
        expected_state_containersready,
        expected_state_ready,
    """,
    [
        (OK, OK, OK, OK, State.OK, State.OK, State.OK, State.OK),
        (OK, OK, OK, WARN, State.OK, State.OK, State.OK, State.WARN),
        (OK, OK, WARN, WARN, State.OK, State.OK, State.WARN, State.WARN),
        (OK, WARN, WARN, WARN, State.OK, State.WARN, State.WARN, State.WARN),
        (WARN, WARN, WARN, WARN, State.WARN, State.WARN, State.WARN, State.WARN),
        (WARN, WARN, WARN, CRIT, State.WARN, State.WARN, State.WARN, State.CRIT),
        (WARN, WARN, CRIT, CRIT, State.WARN, State.WARN, State.CRIT, State.CRIT),
        (WARN, CRIT, CRIT, CRIT, State.WARN, State.CRIT, State.CRIT, State.CRIT),
        (CRIT, CRIT, CRIT, CRIT, State.CRIT, State.CRIT, State.CRIT, State.CRIT),
    ],
    ids=[
        "all_ok",
        "not_ready_warn",
        "containers_not_ready_warn_not_ready_warn",
        "unscheduled_warn_containers_not_ready_warn_not_ready_warn",
        "all_warn",
        "uninitialized_warn_unscheduled_warn_containers_not_ready_warn_not_ready_crit",
        "uninitialized_warn_unscheduled_warn_containers_not_ready_crit_not_ready_crit",
        "uninitialized_warn_unscheduled_crit_containers_not_ready_crit_not_ready_crit",
        "all_crit",
    ],
)
def test_check_results_state_multi_when_status_false(
    expected_state_initialized,
    expected_state_scheduled,
    expected_state_containersready,
    expected_state_ready,
    check_result,
):
    expected_states = [
        expected_state_scheduled,
        expected_state_initialized,
        expected_state_containersready,
        expected_state_ready,
    ]
    assert [r.state for r in check_result] == expected_states


@pytest.mark.parametrize("state", [CRIT])
@pytest.mark.parametrize(
    """
        status_initialized,
        status_scheduled,
        status_containersready,
        status_ready,
        expected_state_initialized,
        expected_state_scheduled,
        expected_state_containersready,
        expected_state_ready,
    """,
    [
        (None, True, None, None, State.CRIT, State.OK, State.CRIT, State.CRIT),
        (True, True, None, None, State.OK, State.OK, State.CRIT, State.CRIT),
        (None, False, None, None, State.CRIT, State.CRIT, State.CRIT, State.CRIT),
        (False, True, None, None, State.CRIT, State.OK, State.CRIT, State.CRIT),
        (False, False, None, None, State.CRIT, State.CRIT, State.CRIT, State.CRIT),
        (False, False, False, False, State.CRIT, State.CRIT, State.CRIT, State.CRIT),
    ],
    ids=[
        "scheduled_ok_others_empty",
        "scheduled_ok_initialized_ok_others_empty",
        "unscheduled_crit_others_empty",
        "scheduled_ok_uninitialized_crit_others_empty",
        "unscheduled_crit_uninitialized_crit_others_empty",
        "all_crit",
    ],
)
def test_check_all_results_with_summary_status_mixed(
    expected_state_initialized,
    expected_state_scheduled,
    expected_state_containersready,
    expected_state_ready,
    check_result,
):
    expected_states = [
        expected_state_scheduled,
        expected_state_initialized,
        expected_state_containersready,
        expected_state_ready,
    ]
    assert [r.state for r in check_result] == expected_states


def test_register_agent_section_calls(agent_section):
    assert str(agent_section.name) == "kube_pod_conditions_v1"
    assert str(agent_section.parsed_section_name) == "kube_pod_conditions"
    assert agent_section.parse_function == kube_pod_conditions.parse


def test_register_check_plugin_calls(check_plugin):
    assert str(check_plugin.name) == "kube_pod_conditions"
    assert check_plugin.service_name == "Condition"
    assert check_plugin.discovery_function.__wrapped__ == kube_pod_conditions.discovery
    assert check_plugin.check_function.__wrapped__ == kube_pod_conditions.check
    assert check_plugin.check_default_parameters == dict(
        scheduled="no_levels",
        initialized="no_levels",
        containersready="no_levels",
        ready="no_levels",
    )
    assert str(check_plugin.check_ruleset_name) == "kube_pod_conditions"
