#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import pytest  # type: ignore[import]

from testlib import get_value_store_fixture, on_time

import cmk.base.plugins.agent_based.local as local
from cmk.base.plugins.agent_based.utils.cache_helper import CacheInfo
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State as state, Metric, IgnoreResults

value_store_fixture = get_value_store_fixture(local)


def test_invalid_metric_name_does_not_crash() -> None:
    assert list(
        local.check_local(
            "MyService",
            {},
            local.parse_local([["0", "MyService", "invalid:name=1", "This", "is", "a", "summary"]]),
        )) == [
            Result(state=state.OK, summary="This is a summary"),
            Result(
                state=state.WARN,
                summary="Invalid metric name: 'invalid:name'",
                details=("The metric name 'invalid:name' is invalid. It will not be recorded. "
                         "Problem: invalid character(s) in metric name: ':'"),
            ),
            Result(state=state.OK, summary="invalid:name: 1.00"),
        ]


@pytest.mark.parametrize('line,expected_output', [
    (
        'service_name some rest',
        ('service_name', ['some', 'rest'], None),
    ),
    (
        '"space separated service name" some rest',
        ('space separated service name', ['some', 'rest'], None),
    ),
    (
        "'space separated service name' some rest",
        ('space separated service name', ['some', 'rest'], None),
    ),
    (
        '',
        (None, None, "too many spaces or missing line content"),
    ),
    (
        ' ',
        (None, None, "too many spaces or missing line content"),
    ),
    (
        ' "space separated service name" some rest',
        (None, None, "too many spaces or missing line content"),
    ),
    (
        '"space separated service name\' some rest',
        (None, None, "missing closing quote character"),
    ),
])
def test_extract_service_name(line, expected_output):
    assert local._extract_service_name(line.split(' ')) == expected_output


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
        (['P  "item name" too many spaces'],
         local.LocalSection(
             errors=[
                 local.LocalError(
                     output='P  "item name" too many spaces',
                     reason='Could not extract service name: too many spaces or missing line content'
                 ),
             ],
             data={},
         )),
        (['P  "item name - missing quote'],
         local.LocalSection(
             errors=[
                 local.LocalError(
                     output='P  "item name - missing quote',
                     reason='Could not extract service name: too many spaces or missing line content'
                 ),
             ],
             data={},
         )),
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
                              Result(state=state.OK, summary="V: 120.00"),
                              Metric("V", 120, boundaries=(0, 1000)),
                          ]


def test_cached(value_store):
    local_result = local.LocalResult(
        cached=CacheInfo(age=61, cache_interval=120),
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
                                          summary=("Cache generated 1 minute 1 second ago, "
                                                   "cache interval: 2 minutes 0 seconds, "
                                                   "elapsed cache lifespan: 50.83%"),
                                      ),
                                  ]


def test_cached_stale(value_store):
    def call(age: int = 421):
        local_result = local.LocalResult(
            cached=CacheInfo(age=age, cache_interval=120),
            item="Cached",
            state=0,
            text="A cached data service",
            perfdata=[],
        )
        with on_time("2021-08-30 14:07:01", "UTC"):
            return list(
                local.check_local(
                    "",
                    {},
                    local.LocalSection(errors=[], data={"": local_result}),
                ))

    # we got current data, we see relative caching info
    assert call(age=5) == [
        Result(state=state.OK, summary="A cached data service"),
        Result(state=state.OK,
               summary="Cache generated 5 seconds ago, "
               "cache interval: 2 minutes 0 seconds, "
               "elapsed cache lifespan: 4.17%"),
    ]

    # we let pass some time and passed the stalness threshold

    # generate message with absolute cache info, to be displayed when service goes stale
    assert call() == [
        Result(state=state.OK, summary="A cached data service"),
        Result(
            state=state.OK,
            summary=("Cache generated Aug 30 2021 14:00:00, "
                     "cache interval: 2 minutes 0 seconds, "
                     "cache lifespan exceeded!"),
        ),
    ]

    # service is now stale. checkmk will display previous summary
    assert call() == [
        Result(state=state.OK, summary="A cached data service"),
        IgnoreResults('Cache expired.'),
    ]

    # we got new data, caching is only five seconds old, so we see relative cache info again
    assert call(age=5) == [
        Result(state=state.OK, summary="A cached data service"),
        Result(state=state.OK,
               summary="Cache generated 5 seconds ago, "
               "cache interval: 2 minutes 0 seconds, "
               "elapsed cache lifespan: 4.17%"),
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


def test_cluster_cached(value_store):
    section: Dict[str, local.LocalSection] = {
        "node0": local.LocalSection(
            errors=[],
            data={
                "item": local.LocalResult(
                    cached=None,
                    item="Clustered service",
                    state=1,
                    text="Service is WARN",
                    perfdata=[],
                )
            },
        ),
        "node1": local.LocalSection(
            errors=[],
            data={
                "item": local.LocalResult(
                    cached=CacheInfo(age=400, cache_interval=120),
                    item="Clustered service",
                    state=2,
                    text="Service is CRIT",
                    perfdata=[],
                )
            },
        ),
    }

    with on_time("2021-09-01 14:06:40", "UTC"):
        assert list(local.cluster_check_local("item", {}, section)) == [
            Result(state=state.CRIT, summary='[node1]: Service is CRIT'),
            Result(state=state.OK,
                   summary="[node1]: Cache generated Sep 01 2021 14:00:00, "
                   "cache interval: 2 minutes 0 seconds, "
                   "cache lifespan exceeded!"),
            Result(state=state.WARN, notice="[node0]: Service is WARN"),
        ]

        assert list(local.cluster_check_local("item", {}, section)) == [
            Result(state=state.WARN, notice="[node0]: Service is WARN"),
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
