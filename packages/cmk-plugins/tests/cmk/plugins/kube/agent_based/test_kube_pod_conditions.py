#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: SLF001  # tests call kube_pod_conditions._check to control `now`


import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import ValidationError

from cmk.agent_based.v2 import render, Result, State, StringTable
from cmk.plugins.kube.agent_based import kube_pod_conditions
from cmk.plugins.kube.kube import VSResultAge
from cmk.plugins.kube.schemata.api import ConditionStatus
from cmk.plugins.kube.schemata.section import PodCondition, PodConditions

MINUTE = 60
TIMESTAMP = 359

REASON = "MuchReason"
DETAIL = "wow detail many detailed"


def _condition_kwargs(status: ConditionStatus, age_minutes: int = 0) -> dict[str, Any]:
    """Common kwargs for a single condition; used by both the JSON payload and
    the PodCondition constructor paths.
    """
    return {
        "status": status,
        "reason": REASON,
        "detail": DETAIL,
        "last_transition_time": TIMESTAMP - age_minutes * MINUTE,
    }


def _payload(status: ConditionStatus | None, age_minutes: int = 0) -> dict[str, Any] | None:
    """JSON-shape payload that parse() consumes for a single condition."""
    return None if status is None else _condition_kwargs(status, age_minutes)


def _section_payload(
    *,
    initialized: ConditionStatus | None = ConditionStatus.TRUE,
    scheduled: ConditionStatus | None = ConditionStatus.TRUE,
    containersready: ConditionStatus | None = ConditionStatus.TRUE,
    ready: ConditionStatus | None = ConditionStatus.TRUE,
    hasnetwork: ConditionStatus | None = ConditionStatus.TRUE,
    readytostartcontainers: ConditionStatus | None = None,
    resizepending: ConditionStatus | None = ConditionStatus.FALSE,
    resizeinprogress: ConditionStatus | None = ConditionStatus.FALSE,
    age_minutes: int = 0,
    disruptiontarget: PodCondition | None = None,
) -> dict[str, Any]:
    """The shared dict shape underneath both the JSON serialization and the
    direct PodConditions construction paths.

    Defaults are picked for test convenience: every condition present and
    "healthy" (ready-chain True, resize conditions False, hasnetwork True,
    readytostartcontainers absent because it's the post-1.28 alias for
    hasnetwork). Tests override only what they care about.

    Passing None for a status drops that condition from the section. Required
    fields (scheduled) will then fail validation, which test_parse_fails_*
    relies on. ``disruptiontarget`` is a full PodCondition because tests that
    use it want a custom reason/detail (e.g. "EvictionByEvictionAPI").
    """
    payload: dict[str, Any] = {
        "initialized": _payload(initialized, age_minutes),
        "hasnetwork": _payload(hasnetwork, age_minutes),
        "readytostartcontainers": _payload(readytostartcontainers, age_minutes),
        "scheduled": _payload(scheduled, age_minutes),
        "containersready": _payload(containersready, age_minutes),
        "ready": _payload(ready, age_minutes),
        "resizepending": _payload(resizepending, age_minutes),
        "resizeinprogress": _payload(resizeinprogress, age_minutes),
    }
    if disruptiontarget is not None:
        payload["disruptiontarget"] = disruptiontarget.model_dump()
    return payload


def _make_string_table(**kwargs: Any) -> StringTable:
    """JSON-encode the section payload as the agent would emit it."""
    return [[json.dumps(_section_payload(**kwargs))]]


def _make_section(**kwargs: Any) -> PodConditions:
    """Build a PodConditions directly from the shared payload shape."""
    return PodConditions(**_section_payload(**kwargs))


def _expected_condition(status: ConditionStatus | None) -> PodCondition | None:
    return None if status is None else PodCondition(**_condition_kwargs(status))


def test_parse() -> None:
    """JSON round-trip"""
    section = kube_pod_conditions.parse(_make_string_table())
    assert section.initialized == _expected_condition(ConditionStatus.TRUE)
    assert section.scheduled == _expected_condition(ConditionStatus.TRUE)
    assert section.containersready == _expected_condition(ConditionStatus.TRUE)
    assert section.ready == _expected_condition(ConditionStatus.TRUE)
    assert section.resizepending == _expected_condition(ConditionStatus.FALSE)
    assert section.resizeinprogress == _expected_condition(ConditionStatus.FALSE)


_T = ConditionStatus.TRUE
_F = ConditionStatus.FALSE


@dataclass(frozen=True)
class _ParseCase:
    name: str
    initialized: ConditionStatus | None
    scheduled: ConditionStatus | None
    containersready: ConditionStatus | None
    ready: ConditionStatus | None
    resizepending: ConditionStatus | None
    resizeinprogress: ConditionStatus | None


@pytest.mark.parametrize(
    "case",
    [
        _ParseCase("all_ok", _T, _T, _T, _T, _F, _F),
        _ParseCase("initialized_scheduled", _T, _T, _F, _F, _F, _F),
        _ParseCase("unscheduled", None, _F, None, None, None, None),
        _ParseCase("unscheduled_uninitialized", _F, _F, None, None, None, None),
        _ParseCase("all_not_ok", _F, _F, _F, _F, _T, _T),
    ],
    ids=lambda c: c.name,
)
def test_parse_multi(case: _ParseCase) -> None:
    """Exercise the JSON->section parse path across various status mixes.

    Each case is a snapshot of a real-world-ish pod state (everything healthy,
    only ready-chain partially initialized, only ``scheduled`` known, etc.).
    None means the condition is absent from the agent output entirely; the
    parser should drop it from the section, not error.
    """
    section = kube_pod_conditions.parse(
        _make_string_table(
            initialized=case.initialized,
            scheduled=case.scheduled,
            containersready=case.containersready,
            ready=case.ready,
            resizepending=case.resizepending,
            resizeinprogress=case.resizeinprogress,
        )
    )
    assert section.initialized == _expected_condition(case.initialized)
    assert section.scheduled == _expected_condition(case.scheduled)
    assert section.containersready == _expected_condition(case.containersready)
    assert section.ready == _expected_condition(case.ready)
    assert section.resizepending == _expected_condition(case.resizepending)
    assert section.resizeinprogress == _expected_condition(case.resizeinprogress)


def test_parse_fails_when_all_conditions_empty() -> None:
    # `scheduled` is required by PodConditions; setting it (and friends) to
    # None should make parse() raise.
    string_table = _make_string_table(
        initialized=None,
        scheduled=None,
        containersready=None,
        ready=None,
    )
    with pytest.raises(ValidationError):
        kube_pod_conditions.parse(string_table)


# ---------------------------------------------------------------------------
# Check-logic tests construct sections directly via _make_section. `age_minutes`
# is the time since the condition's last transition. _TEST_PARAMS sets levels
# that fire at 5min/10min on every condition.
# ---------------------------------------------------------------------------


_TEST_PARAMS: Mapping[str, VSResultAge] = {
    "initialized": ("levels", (5 * MINUTE, 10 * MINUTE)),
    "scheduled": ("levels", (5 * MINUTE, 10 * MINUTE)),
    "containersready": ("levels", (5 * MINUTE, 10 * MINUTE)),
    "ready": ("levels", (5 * MINUTE, 10 * MINUTE)),
    "resizepending": ("levels", (5 * MINUTE, 10 * MINUTE)),
    "resizeinprogress": ("levels", (5 * MINUTE, 10 * MINUTE)),
}

_ALL_NO_LEVELS: Mapping[str, VSResultAge] = {
    "scheduled": "no_levels",
    "initialized": "no_levels",
    "containersready": "no_levels",
    "ready": "no_levels",
}


@pytest.mark.parametrize(
    "ready_status",
    [ConditionStatus.TRUE, ConditionStatus.FALSE],
)
def test_check_all_ok_when_age_is_zero(ready_status: ConditionStatus) -> None:
    """With age_minutes=0 nothing has exceeded any level yet, regardless of status."""
    section = _make_section(
        initialized=ready_status,
        scheduled=ready_status,
        containersready=ready_status,
        ready=ready_status,
    )
    results = list(kube_pod_conditions._check(TIMESTAMP, _TEST_PARAMS, section))
    assert all(isinstance(r, Result) and r.state == State.OK for r in results)


@pytest.mark.parametrize("age_minutes", [0, 5, 10])
def test_check_all_ok_when_status_expected_regardless_of_age(age_minutes: int) -> None:
    """Status matching expectations: never alerts, no matter how old."""
    section = _make_section(age_minutes=age_minutes)
    results = list(kube_pod_conditions._check(TIMESTAMP, _TEST_PARAMS, section))
    assert all(isinstance(r, Result) and r.state == State.OK for r in results)


@pytest.mark.parametrize("age_minutes", [0, 5, 10])
@pytest.mark.parametrize(
    "params",
    [_ALL_NO_LEVELS, {}],
    ids=["no_levels", "no_params"],
)
def test_check_all_ok_when_status_unexpected_but_no_levels_configured(
    age_minutes: int,
    params: Mapping[str, VSResultAge],
) -> None:
    """Unexpected status with no levels (explicit or implicit): no alert."""
    section = _make_section(
        initialized=ConditionStatus.FALSE,
        scheduled=ConditionStatus.FALSE,
        containersready=ConditionStatus.FALSE,
        ready=ConditionStatus.FALSE,
        age_minutes=age_minutes,
    )
    results = list(kube_pod_conditions._check(TIMESTAMP, params, section))
    assert all(isinstance(r, Result) and r.state == State.OK for r in results)


@pytest.mark.parametrize("age_minutes", [0, 5, 10])
def test_check_summaries_when_all_status_unexpected(age_minutes: int) -> None:
    """Each condition's summary reports the wrong status and the time since
    its last transition. Uses params={} so state stays OK regardless of age;
    this exercises summary format and ordering across different age renderings,
    not threshold behavior.
    """
    section = _make_section(
        initialized=ConditionStatus.FALSE,
        scheduled=ConditionStatus.FALSE,
        containersready=ConditionStatus.FALSE,
        ready=ConditionStatus.FALSE,
        hasnetwork=ConditionStatus.FALSE,
        resizepending=ConditionStatus.TRUE,
        resizeinprogress=ConditionStatus.TRUE,
        age_minutes=age_minutes,
    )
    results = list(kube_pod_conditions._check(TIMESTAMP, {}, section))
    time_diff = render.timespan(age_minutes * MINUTE)
    expected = [
        f"{name.upper()}: {value} ({REASON}: {DETAIL}) for {time_diff}"
        for name, value in [
            ("scheduled", False),
            ("hasnetwork", False),
            ("initialized", False),
            ("containersready", False),
            ("ready", False),
            ("resizepending", True),
            ("resizeinprogress", True),
        ]
    ]
    assert [r.summary for r in results if isinstance(r, Result)] == expected


def test_check_disruption_target_condition() -> None:
    section = _make_section(
        disruptiontarget=PodCondition(
            status=ConditionStatus.TRUE,
            reason="EvictionByEvictionAPI",
            detail="EvictionAPI: evicting",
            last_transition_time=TIMESTAMP,
        ),
    )
    results = list(kube_pod_conditions._check(TIMESTAMP, {}, section))
    assert [r.summary for r in results if isinstance(r, Result)] == [
        "SCHEDULED: True",
        "HASNETWORK: True",
        "INITIALIZED: True",
        "CONTAINERSREADY: True",
        "READY: True",
        "RESIZEPENDING: False",
        "RESIZEINPROGRESS: False",
        "DISRUPTIONTARGET: True (EvictionByEvictionAPI: EvictionAPI: evicting)",
    ]


def test_check_handles_unknown_status() -> None:
    """An Unknown condition status is rendered without crashing the check.

    Previously, Unknown was unrepresentable (status was a bool) and would fail
    parsing entirely; now it falls through to the time-based check and is
    reported as 'Unknown' in the service summary.
    """
    section = _make_section(scheduled=ConditionStatus.UNKNOWN)
    assert list(kube_pod_conditions._check(TIMESTAMP, {}, section)) == [
        Result(
            state=State.OK,
            summary=f"SCHEDULED: Unknown ({REASON}: {DETAIL}) for 0 seconds",
        ),
        Result(state=State.OK, summary="HASNETWORK: True"),
        Result(state=State.OK, summary="INITIALIZED: True"),
        Result(state=State.OK, summary="CONTAINERSREADY: True"),
        Result(state=State.OK, summary="READY: True"),
        Result(state=State.OK, summary="RESIZEPENDING: False"),
        Result(state=State.OK, summary="RESIZEINPROGRESS: False"),
    ]
