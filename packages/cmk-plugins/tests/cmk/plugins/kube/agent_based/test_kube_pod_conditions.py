#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"
# ruff: noqa: SLF001  # Private member accessed


import json
from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import ValidationError

from cmk.agent_based.v2 import CheckResult, render, Result, State, StringTable
from cmk.plugins.kube.agent_based import kube_pod_conditions
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


def status_dict(status: bool | None, time_diff_minutes=0) -> Mapping[str, str] | None:
    if status is None:
        return None
    return {
        "status": status,
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
def state_resizepending(state):
    return state


@pytest.fixture
def state_resizeinprogress(state):
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
def status_resizepending():
    return False


@pytest.fixture
def status_resizeinprogress():
    return False


@pytest.fixture
def string_table_element(
    status_initialized,
    status_scheduled,
    status_containersready,
    status_ready,
    status_resizepending,
    status_resizeinprogress,
    state_initialized,
    state_scheduled,
    state_containersready,
    state_ready,
    state_resizepending,
    state_resizeinprogress,
):
    return {
        "initialized": status_dict(status_initialized, state_initialized),
        "hasnetwork": status_dict(True),
        "scheduled": status_dict(status_scheduled, state_scheduled),
        "containersready": status_dict(status_containersready, state_containersready),
        "ready": status_dict(status_ready, state_ready),
        "resizepending": status_dict(status_resizepending, state_resizepending),
        "resizeinprogress": status_dict(status_resizeinprogress, state_resizeinprogress),
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
        "resizepending": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
        "resizeinprogress": ("levels", (WARN * MINUTE, CRIT * MINUTE)),
    }


@pytest.fixture
def check_result(params, section):
    return kube_pod_conditions._check(TIMESTAMP, params, section)


def test_parse(string_table: StringTable) -> None:
    section = kube_pod_conditions.parse(string_table)

    def assert_ready(cond: PodCondition | None, invert: bool = False) -> None:
        if cond is None:
            raise AssertionError("Condition should not be None")
        assert cond.model_dump() == status_dict(not invert)

    assert_ready(section.initialized)
    assert_ready(section.scheduled)
    assert_ready(section.containersready)
    assert_ready(section.ready)
    assert_ready(section.resizepending, invert=True)
    assert_ready(section.resizeinprogress, invert=True)


@pytest.mark.parametrize(
    """
        status_initialized,
        status_scheduled,
        status_containersready,
        status_ready,
        status_resizepending,
        status_resizeinprogress,
        expected_initialized,
        expected_scheduled,
        expected_containersready,
        expected_ready,
        expected_resizepending,
        expected_resizeinprogress,
    """,
    [
        (
            True,
            True,
            True,
            True,
            False,
            False,
            status_dict(True),
            status_dict(True),
            status_dict(True),
            status_dict(True),
            status_dict(False),
            status_dict(False),
        ),
        (
            True,
            True,
            False,
            False,
            False,
            False,
            status_dict(True),
            status_dict(True),
            status_dict(False),
            status_dict(False),
            status_dict(False),
            status_dict(False),
        ),
        (
            None,
            False,
            None,
            None,
            None,
            None,
            None,
            status_dict(False),
            None,
            None,
            None,
            None,
        ),
        (
            False,
            False,
            None,
            None,
            None,
            None,
            status_dict(False),
            status_dict(False),
            None,
            None,
            None,
            None,
        ),
        (
            False,
            False,
            False,
            False,
            True,
            True,
            status_dict(False),
            status_dict(False),
            status_dict(False),
            status_dict(False),
            status_dict(True),
            status_dict(True),
        ),
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
    expected_initialized,
    expected_scheduled,
    expected_containersready,
    expected_ready,
    expected_resizepending,
    expected_resizeinprogress,
    string_table,
):
    expected_initialized = (
        PodCondition(**expected_initialized) if expected_initialized is not None else None
    )
    expected_scheduled = PodCondition(**expected_scheduled)
    expected_containersready = (
        PodCondition(**expected_containersready) if expected_containersready is not None else None
    )
    expected_ready = PodCondition(**expected_ready) if expected_ready is not None else None
    expected_resizepending = (
        PodCondition(**expected_resizepending) if expected_resizepending is not None else None
    )
    expected_resizeinprogress = (
        PodCondition(**expected_resizeinprogress) if expected_resizeinprogress is not None else None
    )
    section = kube_pod_conditions.parse(string_table)
    assert section.initialized == expected_initialized
    assert section.scheduled == expected_scheduled
    assert section.containersready == expected_containersready
    assert section.ready == expected_ready
    assert section.resizepending == expected_resizepending
    assert section.resizeinprogress == expected_resizeinprogress


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


def test_check_all_results_with_summary_status_unexpected():
    section = PodConditionsFactory.build(
        initialized=PodConditionFactory.build(status=False, reason=REASON, detail=DETAIL),
        hasnetwork=PodConditionFactory.build(status=False, reason=REASON, detail=DETAIL),
        scheduled=PodConditionFactory.build(status=False, reason=REASON, detail=DETAIL),
        containersready=PodConditionFactory.build(status=False, reason=REASON, detail=DETAIL),
        ready=PodConditionFactory.build(status=False, reason=REASON, detail=DETAIL),
        resizepending=PodConditionFactory.build(status=True, reason=REASON, detail=DETAIL),
        resizeinprogress=PodConditionFactory.build(status=True, reason=REASON, detail=DETAIL),
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    expected_summaries = [
        f"{k.upper()}: {v} ({REASON}: {DETAIL}) for 0 seconds"
        for (k, v) in [
            ("scheduled", False),
            ("hasnetwork", False),
            ("initialized", False),
            ("containersready", False),
            ("ready", False),
            ("resizepending", True),
            ("resizeinprogress", True),
        ]
    ]
    assert list(r.summary for r in check_result if isinstance(r, Result)) == expected_summaries


@pytest.mark.parametrize("status", [True])
@pytest.mark.parametrize("state", [0, WARN, CRIT])
def test_check_results_state_ok_when_status_expected(
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
def test_check_results_state_ok_when_status_unexpected_and_no_levels(
    check_result: CheckResult,
) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


@pytest.mark.parametrize("status", [False])
@pytest.mark.parametrize("params", [{}])
@pytest.mark.parametrize("state", [OK, WARN, CRIT])
def test_check_results_state_ok_when_status_unexpected_and_no_params(
    check_result: CheckResult,
) -> None:
    assert all(isinstance(r, Result) and r.state == State.OK for r in check_result)


def test_check_results_sets_summary_when_status_unexpected(
    state: float, check_result: CheckResult
) -> None:
    transition_timestamp = TIMESTAMP - state * MINUTE
    pod_condition_with_false_status = PodConditionFactory.build(
        status=False,
        last_transition_time=transition_timestamp,
        reason=REASON,
        detail=DETAIL,
    )
    pod_condition_with_true_status = PodConditionFactory.build(
        status=True,
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
        resizepending=pod_condition_with_true_status,
        resizeinprogress=pod_condition_with_true_status,
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    time_diff = render.timespan(TIMESTAMP - transition_timestamp)
    expected_prefixes = [
        f"{k.upper()}: {v} ({REASON}: {DETAIL}) for {time_diff}"
        for (k, v) in [
            ("scheduled", False),
            ("hasnetwork", False),
            ("initialized", False),
            ("containersready", False),
            ("ready", False),
            ("resizepending", True),
            ("resizeinprogress", True),
            ("disruptiontarget", False),
        ]
    ]
    for expected_prefix, result in zip(expected_prefixes, check_result):
        assert isinstance(result, Result) and result.summary.startswith(expected_prefix)


def test_register_agent_section_calls() -> None:
    agent_section = kube_pod_conditions.agent_section_kube_pod_conditions_v1
    assert agent_section.name == "kube_pod_conditions_v1"
    assert agent_section.parsed_section_name == "kube_pod_conditions"
    assert agent_section.parse_function == kube_pod_conditions.parse


def test_register_check_plugin_calls() -> None:
    check_plugin = kube_pod_conditions.check_plugin_kube_pod_conditions
    assert check_plugin.name == "kube_pod_conditions"
    assert check_plugin.service_name == "Condition"
    assert check_plugin.discovery_function == kube_pod_conditions.discovery
    assert check_plugin.check_function == kube_pod_conditions.check
    assert check_plugin.check_default_parameters == {
        "scheduled": "no_levels",
        "hasnetwork": "no_levels",
        "initialized": "no_levels",
        "containersready": "no_levels",
        "ready": "no_levels",
        "resizepending": ("levels", (300, 600)),
        "resizeinprogress": ("levels", (300, 600)),
    }
    assert check_plugin.check_ruleset_name == "kube_pod_conditions"


def test_check_disruption_target_condition():
    section = PodConditionsFactory.build(
        initialized=PodConditionFactory.build(status=True),
        hasnetwork=PodConditionFactory.build(status=True),
        scheduled=PodConditionFactory.build(status=True),
        containersready=PodConditionFactory.build(status=True),
        ready=PodConditionFactory.build(status=True),
        resizepending=PodConditionFactory.build(status=False),
        resizeinprogress=PodConditionFactory.build(status=False),
        disruptiontarget=PodConditionFactory.build(
            status=True, reason="EvictionByEvictionAPI", detail="EvictionAPI: evicting"
        ),
    )
    check_result = kube_pod_conditions._check(TIMESTAMP, {}, section)
    assert [r.summary for r in check_result if isinstance(r, Result)] == [
        "SCHEDULED: True",
        "HASNETWORK: True",
        "INITIALIZED: True",
        "CONTAINERSREADY: True",
        "READY: True",
        "RESIZEPENDING: False",
        "RESIZEINPROGRESS: False",
        "DISRUPTIONTARGET: True (EvictionByEvictionAPI: EvictionAPI: evicting)",
    ]
