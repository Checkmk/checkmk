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
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.kube import (
    NodeCondition,
    NodeConditions,
    NodeConditionStatus,
)


class NodeConditionFactory(ModelFactory):
    __model__ = NodeCondition


class NodeConditionsFactory(ModelFactory):
    __model__ = NodeConditions

    ready = Use(NodeConditionFactory.build, status=NodeConditionStatus.TRUE)
    memorypressure = Use(NodeConditionFactory.build, status=NodeConditionStatus.FALSE)
    diskpressure = Use(NodeConditionFactory.build, status=NodeConditionStatus.FALSE)
    pidpressure = Use(NodeConditionFactory.build, status=NodeConditionStatus.FALSE)
    networkunavailable = Use(NodeConditionFactory.build, status=NodeConditionStatus.FALSE)


@pytest.fixture
def string_table():
    return [[json.dumps(NodeConditionsFactory.build().dict())]]


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
def section(string_table) -> kube_node_conditions.NodeConditions:
    return kube_node_conditions.parse(string_table)


def test_check_yields_single_result_when_all_conditions_pass(params, section):
    results = list(kube_node_conditions.check(params, section))
    assert len(results) == 1


def test_check_all_results_state_ok(params, section):
    results = list(kube_node_conditions.check(params, section))
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK


def test_check_result_with_falsy_condition_yields_as_much_results_as_section_items(params, section):
    section.diskpressure.status = NodeConditionStatus.TRUE
    results = list(kube_node_conditions.check(params, section))
    assert len(results) == len(list(section))


def test_check_result_with_falsy_condition_yields_one_crit_among_others_ok(params, section):
    section.diskpressure.status = NodeConditionStatus.TRUE
    results = [r for r in kube_node_conditions.check(params, section) if isinstance(r, Result)]
    assert len([result for result in results if result.state == State.CRIT]) == 1
    assert len([result for result in results if result.state == State.OK]) == len(list(section)) - 1
