#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.local as local
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.utils.cache_helper import CacheInfo


@pytest.mark.parametrize(
    "check_line,expected_components",
    [
        ("", None),
        ("0", None),
        ("0 name", None),
        ("0 name -", ("0", "name", "-", None)),
        ('0 "name with space" -', ("0", "name with space", "-", None)),
        ("0 name - info text", ("0", "name", "-", "info text")),
        ("0 name - results' text has a quote", ("0", "name", "-", "results' text has a quote")),
        ("0 name - has a backslash\\", ("0", "name", "-", "has a backslash\\")),
    ],
)
def test_regex_parser(check_line, expected_components):
    assert local._split_check_result(check_line) == expected_components


@pytest.mark.parametrize(
    "string_table,exception_reason",
    [
        (
            [["node_1", "cached(1556005301,300)", "foo"]],
            (
                "Invalid line in agent section <<<local>>>. Reason:"
                " Invalid plugin status node_1."
                ' First offending line: "node_1 cached(1556005301,300) foo"'
            ),
        ),
        (
            [[]],
            (
                "Invalid line in agent section <<<local>>>. Reason:"
                " Received empty line. Maybe some of the local checks"
                " returns a superfluous newline character."
                ' First offending line: ""'
            ),
        ),
    ],
)
def test_local_format_error(string_table, exception_reason):
    with pytest.raises(ValueError) as e:
        list(local.discover_local(local.parse_local(string_table)))
    assert str(e.value) == exception_reason


@pytest.mark.parametrize(
    "string_table_row,expected_parsed_data",
    [
        (
            ["0", "Service_FOO", "V=1", "This", "Check", "is", "OK"],
            local.LocalSection(
                errors=[],
                data={
                    "Service_FOO": local.LocalResult(
                        cache_info=None,
                        item="Service_FOO",
                        state=State.OK,
                        apply_levels=False,
                        text="This Check is OK",
                        perfdata=[
                            local.Perfdata(
                                name="V",
                                value=1.0,
                                levels_upper=None,
                                levels_lower=None,
                                boundaries=(None, None),
                            )
                        ],
                    )
                },
            ),
        ),
        (
            ['0 "Service FOO" V=1 This Check is OK'],  # 1.7: sep(0) + shlex
            local.LocalSection(
                errors=[],
                data={
                    "Service FOO": local.LocalResult(
                        cache_info=None,
                        item="Service FOO",
                        state=State.OK,
                        apply_levels=False,
                        text="This Check is OK",
                        perfdata=[
                            local.Perfdata(
                                name="V",
                                value=1.0,
                                levels_upper=None,
                                levels_lower=None,
                                boundaries=(None, None),
                            )
                        ],
                    )
                },
            ),
        ),
        (
            ["1", "Bar_Service", "-", "This", "is", "WARNING", "and", "has", "no", "metrics"],
            local.LocalSection(
                errors=[],
                data={
                    "Bar_Service": local.LocalResult(
                        cache_info=None,
                        item="Bar_Service",
                        state=State.WARN,
                        apply_levels=False,
                        text="This is WARNING and has no metrics",
                        perfdata=[],
                    )
                },
            ),
        ),
        (
            ["2", "NotGood", "V=120;50;100;0;1000", "A", "critical", "check"],
            local.LocalSection(
                errors=[],
                data={
                    "NotGood": local.LocalResult(
                        cache_info=None,
                        item="NotGood",
                        state=State.CRIT,
                        apply_levels=False,
                        text="A critical check",
                        perfdata=[
                            local.Perfdata(
                                name="V",
                                value=120,
                                levels_upper=(50, 100),
                                levels_lower=None,
                                boundaries=(0, 1000),
                            )
                        ],
                    )
                },
            ),
        ),
        (
            [
                "P",
                "Some_other_Service",
                "value1=10;30;50|value2=20;10:20;0:50;0;100",
                "Result",
                "is",
                "computed",
                "from",
                "two",
                "values",
            ],
            local.LocalSection(
                errors=[],
                data={
                    "Some_other_Service": local.LocalResult(
                        cache_info=None,
                        item="Some_other_Service",
                        state=State.OK,
                        apply_levels=True,
                        text="Result is computed from two values",
                        perfdata=[
                            local.Perfdata(
                                name="value1",
                                value=10,
                                levels_upper=(30, 50),
                                levels_lower=None,
                                boundaries=(None, None),
                            ),
                            local.Perfdata(
                                name="value2",
                                value=20,
                                levels_upper=(20, 50),
                                levels_lower=(10, 0),
                                boundaries=(0, 100),
                            ),
                        ],
                    )
                },
            ),
        ),
        (
            ["P", "No-Text", "hirn=-8;-20"],
            local.LocalSection(
                errors=[],
                data={
                    "No-Text": local.LocalResult(
                        cache_info=None,
                        item="No-Text",
                        state=State.OK,
                        apply_levels=True,
                        text="",
                        perfdata=[
                            local.Perfdata(
                                name="hirn",
                                value=-8,
                                levels_upper=(-20, float("inf")),
                                levels_lower=None,
                                boundaries=(None, None),
                            )
                        ],
                    )
                },
            ),
        ),
        (
            ["P", "D’oh!", "this_is_an_invalid_metric|isotopes=0", "I", "messed", "up!"],
            local.LocalSection(
                errors=[
                    local.LocalError(
                        output="P D’oh! this_is_an_invalid_metric|isotopes=0 I messed up!",
                        reason="Invalid performance data: 'this_is_an_invalid_metric'. ",
                    )
                ],
                data={
                    "D’oh!": local.LocalResult(
                        cache_info=None,
                        item="D’oh!",
                        state=State.UNKNOWN,
                        apply_levels=False,
                        text="Invalid performance data: 'this_is_an_invalid_metric'. Output is: I messed up!",
                        perfdata=[
                            local.Perfdata(
                                name="isotopes",
                                value=0,
                                levels_upper=None,
                                levels_lower=None,
                                boundaries=(None, None),
                            )
                        ],
                    )
                },
            ),
        ),
    ],
)
def test_parse(string_table_row, expected_parsed_data):
    result = local.parse_local([string_table_row])
    print()
    print(string_table_row)
    print(expected_parsed_data)
    print(result)
    assert result == expected_parsed_data


def test_fix_state():
    local_result = local.LocalResult(
        cache_info=None,
        item="NotGood",
        state=State.CRIT,
        apply_levels=False,
        text="A critical check",
        perfdata=[
            local.Perfdata(
                name="V",
                value=120,
                levels_upper=(50, 100),
                levels_lower=None,
                boundaries=(0, 1000),
            )
        ],
    )

    assert list(
        local.check_local(
            "NotGood", {}, local.LocalSection(errors=[], data={"NotGood": local_result})
        )
    ) == [
        Result(state=State.CRIT, summary="A critical check"),
        Result(state=State.OK, summary="V: 120.00"),
        Metric("V", 120, boundaries=(0, 1000)),
    ]


@pytest.mark.parametrize(
    "age,expected",
    [
        (
            60,
            "Cache generated 1 minute 0 seconds ago, cache interval: 2 minutes 0 seconds, "
            "elapsed cache lifespan: 50.00%",
        ),
        (
            -60,
            "Cannot reasonably calculate cache metrics (hosts time is running ahead), cache interval: 2 minutes 0 seconds",
        ),
    ],
)
def test_cached(age, expected):
    local_result = local.LocalResult(
        cache_info=CacheInfo(
            age=age,
            cache_interval=120,
        ),
        item="Cached",
        state=State.OK,
        apply_levels=False,
        text="A cached data service",
        perfdata=[],
    )

    assert list(
        local.check_local("", {}, local.LocalSection(errors=[], data={"": local_result}))
    ) == [
        Result(state=State.OK, summary="A cached data service"),
        Result(
            state=State.OK,
            summary=f"{expected}",
        ),
    ]


def test_compute_state():
    local_result = local.LocalResult(
        cache_info=None,
        item="Some_other_Service",
        state=State.OK,
        apply_levels=True,
        text="Result is computed from two values",
        perfdata=[
            local.Perfdata(
                name="value1",
                value=10,
                levels_upper=(30, 50),
                levels_lower=None,
                boundaries=(None, None),
            ),
            local.Perfdata(
                name="value2",
                value=20,
                levels_upper=(20, 50),
                levels_lower=(10, 0),
                boundaries=(0, 100),
            ),
        ],
    )

    assert list(
        local.check_local("", {}, local.LocalSection(errors=[], data={"": local_result}))
    ) == [
        Result(state=State.OK, summary="Result is computed from two values"),
        Result(state=State.OK, summary="Value 1: 10.00"),
        Metric("value1", 10, levels=(30.0, 50.0)),
        Result(state=State.WARN, summary="Value 2: 20.00 (warn/crit at 20.00/50.00)"),
        Metric("value2", 20, levels=(20, 50), boundaries=(0, 100)),
    ]


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os

    from tests.testlib.utils import cmk_path

    assert not pytest.main(
        ["--doctest-modules", os.path.join(cmk_path(), "cmk/base/plugins/agent_based/local.py")]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
