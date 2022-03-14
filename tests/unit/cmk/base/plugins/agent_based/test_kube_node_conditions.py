#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import json

import pytest
from pydantic_factories import ModelFactory, Use

from cmk.base.plugins.agent_based import kube_node_conditions
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils import kube


class NodeConditionFactory(ModelFactory):
    __model__ = kube.NodeCondition


class NodeConditionsFactory(ModelFactory):
    __model__ = kube.NodeConditions

    ready = Use(NodeConditionFactory.build, status=kube.NodeConditionStatus.TRUE)
    memorypressure = Use(NodeConditionFactory.build, status=kube.NodeConditionStatus.FALSE)
    diskpressure = Use(NodeConditionFactory.build, status=kube.NodeConditionStatus.FALSE)
    pidpressure = Use(NodeConditionFactory.build, status=kube.NodeConditionStatus.FALSE)
    networkunavailable = Use(NodeConditionFactory.build, status=kube.NodeConditionStatus.FALSE)


class FalsyNodeCustomConditionFactory(ModelFactory):
    __model__ = kube.FalsyNodeCustomCondition


class NodeCustomConditionsFactory(ModelFactory):
    __model__ = kube.NodeCustomConditions

    custom_conditions = Use(
        FalsyNodeCustomConditionFactory.batch,
        status=kube.NodeConditionStatus.FALSE,
        size=1,
    )


@pytest.fixture
def params():
    return dict(
        ready=int(State.CRIT),
        memorypressure=int(State.CRIT),
        diskpressure=int(State.CRIT),
        pidpressure=int(State.CRIT),
        networkunavailable=int(State.CRIT),
    )


@pytest.fixture
def string_table():
    return [[json.dumps(NodeConditionsFactory.build().dict())]]


@pytest.fixture
def custom_string_table():
    return [[json.dumps(NodeCustomConditionsFactory.build().dict())]]


@pytest.fixture
def section(string_table) -> kube_node_conditions.NodeConditions:
    return kube_node_conditions.parse_node_conditions(string_table)


@pytest.fixture
def custom_section(custom_string_table) -> kube_node_conditions.NodeCustomConditions:
    return kube_node_conditions.parse_node_custom_conditions(custom_string_table)


@pytest.fixture
def check_result(params, section, custom_section) -> CheckResult:
    return kube_node_conditions.check(params, section, custom_section)


@pytest.mark.parametrize("section", [None])
def test_check_raises_when_section_is_none(check_result):
    with pytest.raises(IgnoreResultsError):
        list(check_result)


def test_check_yields_single_result_when_all_conditions_pass(check_result):
    results = list(check_result)
    assert len(results) == 1


def test_check_all_results_state_ok(check_result):
    results = list(check_result)
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK


@pytest.mark.parametrize(
    "disk_pressure_status",
    [
        kube.NodeConditionStatus.TRUE,
        kube.NodeConditionStatus.UNKNOWN,
    ],
)
def test_check_with_falsy_condition_yields_as_much_results_as_section_items(
    disk_pressure_status, section, custom_section, check_result
):
    section.diskpressure.status = disk_pressure_status
    results = list(check_result)
    assert len(results) == len(list(section)) + len(list(custom_section))


@pytest.mark.parametrize(
    "disk_pressure_status",
    [
        kube.NodeConditionStatus.TRUE,
        kube.NodeConditionStatus.UNKNOWN,
    ],
)
def test_check_with_falsy_condition_yields_one_crit_among_others_ok(
    disk_pressure_status, section, custom_section, check_result
):
    section.diskpressure.status = disk_pressure_status
    expected_ok_results = len(list(section)) + len(list(custom_section)) - 1
    results = [r for r in check_result if isinstance(r, Result)]
    assert len([result for result in results if result.state == State.CRIT]) == 1
    assert len([result for result in results if result.state == State.OK]) == expected_ok_results


def test_check_ignores_missing_network_unavailable_when_all_conditions_pass(section, check_result):
    section.networkunavailable = None
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1


@pytest.mark.parametrize(
    "disk_pressure_status",
    [
        kube.NodeConditionStatus.TRUE,
        kube.NodeConditionStatus.UNKNOWN,
    ],
)
def test_check_ignores_missing_network_unavailable_when_a_condition_does_not_pass(
    disk_pressure_status, section, custom_section, check_result
):
    section.networkunavailable = None
    section.diskpressure.status = disk_pressure_status
    expected_ok_results = len(list(section)) + len(list(custom_section)) - 2
    results = [r for r in check_result if isinstance(r, Result)]
    assert len([result for result in results if result.state == State.CRIT]) == 1
    assert len([result for result in results if result.state == State.OK]) == expected_ok_results


def test_check_with_missing_network_unavailable_all_states_ok(section, check_result):
    section.networkunavailable = None
    results = list(check_result)
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK


def test_check_with_builtin_conditions_true_but_one_false_custom_condition(
    section, custom_section, check_result
):
    custom_section.custom_conditions[0].status = kube.NodeConditionStatus.TRUE
    expected_ok_results = len(list(section)) + len(list(custom_section)) - 1
    results = list(check_result)
    assert len([result for result in results if result.state == State.CRIT]) == 1
    assert len([result for result in results if result.state == State.OK]) == expected_ok_results
