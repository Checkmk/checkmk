#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import kube_node_conditions
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, Result, State

from cmk.plugins.lib.kube import (
    NodeCondition,
    NodeConditions,
    NodeConditionStatus,
    NodeCustomCondition,
    NodeCustomConditions,
)

PARAMS = kube_node_conditions.Params(
    ready=int(State.CRIT),
    memorypressure=int(State.CRIT),
    diskpressure=int(State.CRIT),
    pidpressure=int(State.CRIT),
    networkunavailable=int(State.CRIT),
)


def test_check_raises_when_section_is_none() -> None:
    custom_section = NodeCustomConditions(custom_conditions=[])
    with pytest.raises(IgnoreResultsError):
        list(kube_node_conditions.check(PARAMS, None, custom_section))


def test_check_ignores_missing_network_unavailable() -> None:
    # Act
    results = list(kube_node_conditions._check_condition("networkunavailable", PARAMS, None))
    # Assert
    assert not results


def test_check_all_conditions_ok() -> None:
    section = NodeConditions(
        ready=NodeCondition(status=NodeConditionStatus.TRUE),
        memorypressure=NodeCondition(status=NodeConditionStatus.FALSE),
        diskpressure=NodeCondition(status=NodeConditionStatus.FALSE),
        pidpressure=NodeCondition(status=NodeConditionStatus.FALSE),
        networkunavailable=NodeCondition(status=NodeConditionStatus.FALSE),
    )
    custom_section = NodeCustomConditions(
        custom_conditions=[NodeCustomCondition(type_="custom", status=NodeConditionStatus.FALSE)]
    )
    results = list(kube_node_conditions.check(PARAMS, section, custom_section))
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
    section = NodeConditions(
        ready=NodeCondition(status=NodeConditionStatus.TRUE),
        memorypressure=NodeCondition(status=NodeConditionStatus.TRUE),
        diskpressure=NodeCondition(status=NodeConditionStatus.FALSE),
        pidpressure=NodeCondition(status=NodeConditionStatus.FALSE),
        networkunavailable=NodeCondition(status=NodeConditionStatus.FALSE),
    )
    custom_section = NodeCustomConditions(custom_conditions=[])
    results = list(kube_node_conditions.check(PARAMS, section, custom_section))
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


def test_check_custom() -> None:
    custom_section = NodeCustomConditions(
        custom_conditions=[NodeCustomCondition(type_="custom", status=NodeConditionStatus.TRUE)]
    )
    results = list(kube_node_conditions._check_node_custom_conditions(custom_section))
    assert results == [Result(state=State.CRIT, summary="CUSTOM: True (None: None)")]
