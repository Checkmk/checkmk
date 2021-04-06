#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import pytest  # type: ignore[import]

import cmk.base.plugins.agent_based.local as local
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State as state, Metric


@pytest.mark.parametrize('string_table,exception_reason', [
    (
        [['node_1', 'cached(1556005301,300)', 'foo']],
        ("Invalid line in agent section <<<local>>>. "
         "Reason: Received wrong format of local check output. "
         "Please read the documentation regarding the correct format: "
         "https://docs.checkmk.com/2.0.0/de/localchecks.html  "
         "First offending line: \"node_1 cached(1556005301,300) foo\""),
    ),
    (
        [[]],
        ("Invalid line in agent section <<<local>>>. Reason: Received empty line. "
         "Did any of your local checks returned a superfluous newline character? "
         "First offending line: \"\""),
    ),
])
def test_local_format_error(string_table, exception_reason):

    with pytest.raises(ValueError) as e:
        list(local.discover_local(local.parse_local(string_table)))
    assert str(e.value) == exception_reason


@pytest.mark.parametrize(
    "string_table_row,expected_parsed_data",
    [
        (
            ['0', 'Service_FOO', 'V=1', 'This', 'Check', 'is', 'OK'],
            local.LocalSection(errors=[],
                               data={
                                   "Service_FOO": local.LocalResult(
                                       cached=None,
                                       item="Service_FOO",
                                       state=0,
                                       text="This Check is OK",
                                       perfdata=[
                                           local.Perfdata(
                                               name="V",
                                               value=1.0,
                                               levels=(None, None, None, None),
                                               tuple=("V", 1.0, None, None, None, None),
                                           )
                                       ],
                                   )
                               }),
        ),
        (
            ['0 "Service FOO" V=1 This Check is OK'],  # 1.7: sep(0) + shlex
            local.LocalSection(errors=[],
                               data={
                                   "Service FOO": local.LocalResult(
                                       cached=None,
                                       item="Service FOO",
                                       state=0,
                                       text="This Check is OK",
                                       perfdata=[
                                           local.Perfdata(
                                               name="V",
                                               value=1.0,
                                               levels=(None, None, None, None),
                                               tuple=("V", 1.0, None, None, None, None),
                                           )
                                       ],
                                   )
                               }),
        ),
        (
            ['1', 'Bar_Service', '-', 'This', 'is', 'WARNING', 'and', 'has', 'no', 'metrics'],
            local.LocalSection(errors=[],
                               data={
                                   "Bar_Service": local.LocalResult(
                                       cached=None,
                                       item="Bar_Service",
                                       state=1,
                                       text="This is WARNING and has no metrics",
                                       perfdata=[],
                                   )
                               }),
        ),
        (
            ['2', 'NotGood', 'V=120;50;100;0;1000', 'A', 'critical', 'check'],
            local.LocalSection(errors=[],
                               data={
                                   "NotGood": local.LocalResult(
                                       cached=None,
                                       item="NotGood",
                                       state=2,
                                       text="A critical check",
                                       perfdata=[
                                           local.Perfdata(
                                               name="V",
                                               value=120,
                                               levels=(50, 100, None, None),
                                               tuple=("V", 120, 50, 100, 0, 1000),
                                           )
                                       ],
                                   )
                               }),
        ),
        (
            [
                'P', 'Some_other_Service', 'value1=10;30;50|value2=20;10:20;0:50;0;100', 'Result',
                'is', 'computed', 'from', 'two', 'values'
            ],
            local.LocalSection(errors=[],
                               data={
                                   "Some_other_Service": local.LocalResult(
                                       cached=None,
                                       item="Some_other_Service",
                                       state='P',
                                       text="Result is computed from two values",
                                       perfdata=[
                                           local.Perfdata(
                                               name="value1",
                                               value=10,
                                               levels=(30, 50, None, None),
                                               tuple=("value1", 10, 30, 50, None, None),
                                           ),
                                           local.Perfdata(
                                               name="value2",
                                               value=20,
                                               levels=(20, 50, 10, 0),
                                               tuple=("value2", 20, 20, 50, 0, 100),
                                           )
                                       ],
                                   )
                               }),
        ),
        (
            ['P', 'No-Text', 'hirn=-8;-20'],
            local.LocalSection(errors=[],
                               data={
                                   "No-Text": local.LocalResult(
                                       cached=None,
                                       item="No-Text",
                                       state='P',
                                       text="",
                                       perfdata=[
                                           local.Perfdata(
                                               name="hirn",
                                               value=-8,
                                               levels=(-20, float('inf'), None, None),
                                               tuple=("hirn", -8, -20, None, None, None),
                                           )
                                       ],
                                   )
                               }),
        ),
        (
            ['P', "D'oh!", 'this is an invalid metric|isotopes=0', 'I', 'messed', 'up!'],
            local.LocalSection(
                errors=[],
                data={
                    "D'oh!": local.LocalResult(
                        cached=None,
                        item="D'oh!",
                        state=3,
                        text=
                        "Invalid performance data: 'this is an invalid metric'. Output is: I messed up!",
                        perfdata=[
                            local.Perfdata(
                                name="isotopes",
                                value=0,
                                levels=(None, None, None, None),
                                tuple=("isotopes", 0, None, None, None, None),
                            )
                        ],
                    )
                }),
        ),
    ])
def test_parse(string_table_row, expected_parsed_data):
    assert local.parse_local([string_table_row]) == expected_parsed_data


def test_fix_state():
    local_result = local.LocalResult(
        cached=None,
        item="NotGood",
        state=2,
        text="A critical check",
        perfdata=[
            local.Perfdata(
                name="V",
                value=120,
                levels=(50, 100, None, None),
                tuple=("V", 120, 50, 100, 0, 1000),
            )
        ],
    )

    assert list(
        local.check_local("NotGood", {},
                          local.LocalSection(errors=[], data={"NotGood": local_result}))) == [
                              Result(state=state.CRIT, summary="A critical check"),
                              Metric("V", 120, levels=(50, 100), boundaries=(0, 1000)),
                          ]


def test_cached():
    local_result = local.LocalResult(
        cached=(361, 314, 120),
        item="Cached",
        state=0,
        text="A cached data service",
        perfdata=[],
    )

    assert list(local.check_local("", {},
                                  local.LocalSection(errors=[], data={"": local_result}))) == [
                                      Result(state=state.OK, summary="A cached data service"),
                                      Result(
                                          state=state.OK,
                                          summary=("Cache generated 6 minutes 1 second ago, "
                                                   "Cache interval: 2 minutes 0 seconds, "
                                                   "Elapsed cache lifespan: 314.00%"),
                                      ),
                                  ]


def test_compute_state():
    local_result = local.LocalResult(
        cached=None,
        item="Some_other_Service",
        state='P',
        text="Result is computed from two values",
        perfdata=[
            local.Perfdata(
                name="value1",
                value=10,
                levels=(30, 50, None, None),
                tuple=("value1", 10, 30, 50, None, None),
            ),
            local.Perfdata(
                name="value2",
                value=20,
                levels=(20, 50, 10, 0),
                tuple=("value2", 20, 20, 50, 0, 100),
            )
        ],
    )

    assert list(local.check_local("", {},
                                  local.LocalSection(errors=[], data={"": local_result}))) == [
                                      Result(state=state.OK,
                                             summary="Result is computed from two values"),
                                      Result(state=state.OK, summary="value1: 10.00"),
                                      Metric("value1", 10, levels=(30.0, 50.0)),
                                      Result(state=state.WARN,
                                             summary="value2: 20.00 (warn/crit at 20.00/50.00)"),
                                      Metric("value2", 20, levels=(20, 50), boundaries=(0, 100)),
                                  ]


def test_cluster():
    section: Dict[str, local.LocalSection] = {
        "node0": local.LocalSection(errors=[],
                                    data={
                                        "item": local.LocalResult(
                                            cached=None,
                                            item="Clustered service",
                                            state=0,
                                            text="Service is OK",
                                            perfdata=[],
                                        )
                                    }),
        "node1": local.LocalSection(errors=[],
                                    data={
                                        "item": local.LocalResult(
                                            cached=None,
                                            item="Clustered service",
                                            state=1,
                                            text="Service is WARN",
                                            perfdata=[],
                                        )
                                    }),
        "node2": local.LocalSection(errors=[],
                                    data={
                                        "item": local.LocalResult(
                                            cached=None,
                                            item="Clustered service",
                                            state=2,
                                            text="Service is CRIT",
                                            perfdata=[],
                                        )
                                    }),
    }

    worst = local.cluster_check_local("item", {}, section)
    best = local.cluster_check_local("item", {"outcome_on_cluster": "best"}, section)

    assert list(worst) == [
        Result(state=state.CRIT, notice="[node2]: Service is CRIT"),
        Result(state=state.OK, notice="[node0]: Service is OK"),
        Result(state=state.WARN, notice="[node1]: Service is WARN"),
    ]
    assert list(best) == [
        Result(state=state.OK, summary="[node0]: Service is OK"),
        Result(state=state.OK, notice="[node1]: Service is WARN(!)"),
        Result(state=state.OK, notice="[node2]: Service is CRIT(!!)"),
    ]


def test_cluster_missing_item():
    section: Dict[str, local.LocalSection] = {
        "node0": local.LocalSection(errors=[],
                                    data={
                                        "item": local.LocalResult(
                                            cached=None,
                                            item="Clustered service",
                                            state=0,
                                            text="Service is OK",
                                            perfdata=[],
                                        )
                                    }),
        "node1": local.LocalSection(errors=[], data={}),
    }

    worst = local.cluster_check_local("item", {}, section)
    best = local.cluster_check_local("item", {"outcome_on_cluster": "best"}, section)

    assert list(worst) == [
        Result(state=state.OK, summary="[node0]: Service is OK"),
    ]
    assert list(best) == [
        Result(state=state.OK, summary="[node0]: Service is OK"),
    ]
