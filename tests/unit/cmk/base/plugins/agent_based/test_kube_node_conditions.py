#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import kube_node_conditions
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, Result, State

from cmk.plugins.lib import kube

PARAMS = kube_node_conditions.Params(
    ready=int(State.CRIT),
    memorypressure=int(State.CRIT),
    diskpressure=int(State.CRIT),
    pidpressure=int(State.CRIT),
    networkunavailable=int(State.CRIT),
)


def test_check_raises_when_section_is_none() -> None:
    custom_section = kube.NodeCustomConditions(custom_conditions=[])
    with pytest.raises(IgnoreResultsError):
        list(kube_node_conditions.check(PARAMS, None, custom_section))


def test_check_ignores_missing_network_unavailable() -> None:
    # Act
    results = list(kube_node_conditions._check_condition("networkunavailable", PARAMS, None))
    # Assert
    assert not results


def test_check_all_conditions_ok() -> None:
    section = kube.NodeConditions(
        ready=kube.NodeCondition(status=kube.NodeConditionStatus.TRUE),
        memorypressure=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
        diskpressure=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
        pidpressure=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
        networkunavailable=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
    )
    custom_section = kube.NodeCustomConditions(
        custom_conditions=[
            kube.NodeCustomCondition(type_="custom", status=kube.NodeConditionStatus.FALSE)
        ]
    )
    results = list(kube_node_conditions.check(PARAMS, section, custom_section))
    assert results == [
        Result(state=State.OK, summary="Ready, all conditions passed"),
        Result(state=State.OK, notice="READY: NodeConditionStatus.TRUE (None: None)"),
        Result(
            state=State.OK,
            notice="MEMORYPRESSURE: NodeConditionStatus.FALSE (None: None)",
        ),
        Result(
            state=State.OK,
            notice="DISKPRESSURE: NodeConditionStatus.FALSE (None: None)",
        ),
        Result(
            state=State.OK,
            notice="PIDPRESSURE: NodeConditionStatus.FALSE (None: None)",
        ),
        Result(state=State.OK, notice="NETWORKUNAVAILABLE: NodeConditionStatus.FALSE (None: None)"),
        Result(
            state=State.OK,
            notice="CUSTOM: NodeConditionStatus.FALSE (None: None)",
        ),
    ]


def test_check_one_condition_bad() -> None:
    section = kube.NodeConditions(
        ready=kube.NodeCondition(status=kube.NodeConditionStatus.TRUE),
        memorypressure=kube.NodeCondition(status=kube.NodeConditionStatus.TRUE),
        diskpressure=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
        pidpressure=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
        networkunavailable=kube.NodeCondition(status=kube.NodeConditionStatus.FALSE),
    )
    custom_section = kube.NodeCustomConditions(custom_conditions=[])
    results = list(kube_node_conditions.check(PARAMS, section, custom_section))
    assert results == [
        Result(
            state=State.OK,
            summary="READY: NodeConditionStatus.TRUE",
            details="READY: NodeConditionStatus.TRUE (None: None)",
        ),
        Result(
            state=State.CRIT,
            summary="MEMORYPRESSURE: NodeConditionStatus.TRUE (None: None)",
        ),
        Result(
            state=State.OK,
            summary="DISKPRESSURE: NodeConditionStatus.FALSE",
            details="DISKPRESSURE: NodeConditionStatus.FALSE (None: None)",
        ),
        Result(
            state=State.OK,
            summary="PIDPRESSURE: NodeConditionStatus.FALSE",
            details="PIDPRESSURE: NodeConditionStatus.FALSE (None: None)",
        ),
        Result(
            state=State.OK,
            summary="NETWORKUNAVAILABLE: NodeConditionStatus.FALSE",
            details="NETWORKUNAVAILABLE: NodeConditionStatus.FALSE (None: None)",
        ),
    ]


def test_check_custom() -> None:
    custom_section = kube.NodeCustomConditions(
        custom_conditions=[
            kube.NodeCustomCondition(type_="custom", status=kube.NodeConditionStatus.TRUE)
        ]
    )
    results = list(kube_node_conditions._check_node_custom_conditions(custom_section))
    assert results == [
        Result(state=State.CRIT, summary="CUSTOM: NodeConditionStatus.TRUE (None: None)")
    ]
