#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_node_conditions import (
    _check_condition,
    check,
    DEFAULT_PARAMS,
    DEFAULT_STATE_MAP,
)
from cmk.plugins.kube.schemata.api import NodeConditionStatus
from cmk.plugins.kube.schemata.section import NodeCondition, NodeConditions

READY = NodeCondition(
    type_="Ready",
    status=NodeConditionStatus.TRUE,
    reason=None,
    message=None,
)

MEMORYPRESSURE = NodeCondition(
    type_="MemoryPressure",
    status=NodeConditionStatus.TRUE,
    reason=None,
    message=None,
)

NO_MEMORYPRESSURE = NodeCondition(
    type_="MemoryPressure",
    status=NodeConditionStatus.FALSE,
    reason=None,
    message=None,
)

NO_DISKPRESSURE = NodeCondition(
    type_="DiskPressure",
    status=NodeConditionStatus.FALSE,
    reason=None,
    message=None,
)

NO_PIDPRESSURE = NodeCondition(
    type_="PIDPressure",
    status=NodeConditionStatus.FALSE,
    reason=None,
    message=None,
)

NETWORKAVAILABLE = NodeCondition(
    type_="NetworkUnavailable",
    status=NodeConditionStatus.FALSE,
    reason=None,
    message=None,
)

CUSTOMFALSE = NodeCondition(
    type_="Custom",
    status=NodeConditionStatus.FALSE,
    reason=None,
    message=None,
)

CUSTOMTRUE = NodeCondition(
    type_="Custom",
    status=NodeConditionStatus.TRUE,
    reason=None,
    message=None,
)


def test_check_all_conditions_ok() -> None:
    conditions = [
        READY,
        NO_MEMORYPRESSURE,
        NO_DISKPRESSURE,
        NO_PIDPRESSURE,
        NETWORKAVAILABLE,
        CUSTOMFALSE,
    ]
    section = NodeConditions(conditions=conditions)
    results = list(check(DEFAULT_PARAMS, section))
    assert results == [
        Result(state=State.OK, summary="Ready, all conditions passed"),
        Result(state=State.OK, notice="READY: True (None: None)"),
        Result(state=State.OK, notice="MEMORYPRESSURE: False (None: None)"),
        Result(state=State.OK, notice="DISKPRESSURE: False (None: None)"),
        Result(state=State.OK, notice="PIDPRESSURE: False (None: None)"),
        Result(state=State.OK, notice="NETWORKUNAVAILABLE: False (None: None)"),
        Result(state=State.OK, notice="CUSTOM: False (None: None)"),
    ]


def test_check_one_condition_bad() -> None:
    conditions = [
        READY,
        MEMORYPRESSURE,
        NO_DISKPRESSURE,
        NO_PIDPRESSURE,
        NETWORKAVAILABLE,
    ]
    section = NodeConditions(conditions=conditions)
    results = list(check(DEFAULT_PARAMS, section))
    assert results == [
        Result(
            state=State.OK,
            summary="READY: True",
            details="READY: True (None: None)",
        ),
        Result(
            state=State.CRIT,
            summary="MEMORYPRESSURE: True (None: None)",
        ),
        Result(
            state=State.OK,
            summary="DISKPRESSURE: False",
            details="DISKPRESSURE: False (None: None)",
        ),
        Result(
            state=State.OK,
            summary="PIDPRESSURE: False",
            details="PIDPRESSURE: False (None: None)",
        ),
        Result(
            state=State.OK,
            summary="NETWORKUNAVAILABLE: False",
            details="NETWORKUNAVAILABLE: False (None: None)",
        ),
    ]


def test_check_single() -> None:
    section = NodeConditions(conditions=[CUSTOMTRUE])
    results = list(check(DEFAULT_PARAMS, section))
    assert results == [Result(state=State.CRIT, summary="CUSTOM: True (None: None)")]


def test_check_details() -> None:
    cond = NodeCondition(type_="Ready", status=NodeConditionStatus.TRUE, reason="r", message="m")
    results = list(_check_condition(DEFAULT_STATE_MAP, cond))
    assert results == [Result(state=State.CRIT, summary="READY: True (r: m)")]
