#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import local
from cmk.plugins.lib.cache_helper import CacheInfo


def test_invalid_metric_name_does_not_crash() -> None:
    assert list(
        local.check_local(
            "MyService",
            {},
            local.parse_local([["0", "MyService", "invalid:name=1", "This", "is", "a", "summary"]]),
        )
    ) == [
        Result(state=State.OK, summary="This is a summary"),
        Result(
            state=State.WARN,
            summary="Invalid metric name: 'invalid:name'",
            details=(
                "The metric name 'invalid:name' is invalid. It will not be recorded. "
                "Problem: invalid character(s) in metric name: ':'"
            ),
        ),
        Result(state=State.OK, notice="Invalid:name: 1.00"),
    ]


def test_error_does_not_raise() -> None:
    assert list(
        local.check_local(
            "MyService",
            {},
            local.parse_local([["ARGL", "MyService", "-", "Whopwhop"]]),
        )
    ) == [
        Result(
            state=State.UNKNOWN,
            summary="Invalid data: 'ARGL MyService - Whopwhop'",
            details=(
                "The monitoring site got invalid data from a local check on the monitored host.\n"
                "Invalid data: 'ARGL MyService - Whopwhop'\nReason: Invalid plug-in status ARGL."
            ),
        )
    ]


@pytest.mark.parametrize(
    "check_line,expected_components",
    [
        ("", None),
        ("0", None),
        ("0 name", None),
        ("0 name -", ("0", "name", "-", None)),
        ('0 "name with space" -', ("0", "name with space", "-", None)),
        (
            '0 "name with space"  metric=0   info with spaces',
            ("0", "name with space", "metric=0", "info with spaces"),
        ),
        ("0 name - info text", ("0", "name", "-", "info text")),
        ("0 name - results' text has a quote", ("0", "name", "-", "results' text has a quote")),
        ("0 name - has a backslash\\", ("0", "name", "-", "has a backslash\\")),
    ],
)
def test_regex_parser(
    check_line: str, expected_components: tuple[str, str, str, str | None] | None
) -> None:
    assert local._split_check_result(check_line) == expected_components


@pytest.mark.parametrize(
    "string_table_row,expected_parsed_data",
    [
        pytest.param(
            ["0", "Service_FOO", "V=1", "This", "Check", "is", "OK"],
            local.LocalSection(
                errors={},
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
            id="state OK, input without quotes",
        ),
        pytest.param(
            ['0 "Service FOO" V=1 This Check is OK'],  # 1.7: sep(0) + shlex
            local.LocalSection(
                errors={},
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
            id="state OK, input with quotes",
        ),
        pytest.param(
            ["1", "Bar_Service", "-", "This", "is", "WARNING", "and", "has", "no", "metrics"],
            local.LocalSection(
                errors={},
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
            id="state WARN, no metrics",
        ),
        pytest.param(
            ["2", "NotGood", "V=120;50;100;0;1000", "A", "critical", "check"],
            local.LocalSection(
                errors={},
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
            id="state CRIT",
        ),
        pytest.param(
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
                errors={},
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
            id="multiple metrics",
        ),
        pytest.param(
            ["P", "No-Text", "hirn=-8;-20"],
            local.LocalSection(
                errors={},
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
            id="no text",
        ),
        pytest.param(
            ["P", "D’oh!", "this_is_an_invalid_metric|isotopes=0", "I", "messed", "up!"],
            local.LocalSection(
                errors={
                    "D’oh!": local.LocalError(
                        output="P D’oh! this_is_an_invalid_metric|isotopes=0 I messed up!",
                        reason="Invalid performance data: 'this_is_an_invalid_metric'. ",
                    )
                },
                data={},
            ),
            id="invalid format, invalid metric data",
        ),
        pytest.param(
            ["node_1", "cached(1556005301,300)", "foo"],
            local.LocalSection(
                errors={
                    "cached(1556005301,300)": local.LocalError(
                        output="node_1 cached(1556005301,300) foo",
                        reason="Invalid plug-in status node_1.",
                    )
                },
                data={},
            ),
            id="invalid format, invalid status",
        ),
        pytest.param(
            [],
            local.LocalSection(
                errors={},
                data={},
            ),
            id="invalid format, empty line",
        ),
        pytest.param(
            ["CannotSeparateThis"],
            local.LocalSection(
                errors={
                    "Line #1": local.LocalError(
                        output="CannotSeparateThis",
                        reason="Could not parse line into components (status, service name, performance data, status detail)",
                    )
                },
                data={},
            ),
            id="invalid format, cannot separate",
        ),
    ],
)
def test_parse(string_table_row: list[str], expected_parsed_data: local.LocalSection) -> None:
    assert local.parse_local([string_table_row]) == expected_parsed_data


def test_fix_state() -> None:
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
            "NotGood",
            {},
            local.LocalSection(errors={}, data={"NotGood": local_result}),
        )
    ) == [
        Result(state=State.CRIT, summary="A critical check"),
        Result(state=State.OK, notice="V: 120.00"),
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
def test_cached(age: float, expected: float) -> None:
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
        local.check_local("", {}, local.LocalSection(errors={}, data={"": local_result}))
    ) == [
        Result(state=State.OK, summary="A cached data service"),
        Result(
            state=State.OK,
            summary=f"{expected}",
        ),
    ]


def test_compute_state() -> None:
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
        local.check_local("", {}, local.LocalSection(errors={}, data={"": local_result}))
    ) == [
        Result(state=State.OK, summary="Result is computed from two values"),
        Result(state=State.OK, notice="Value 1: 10.00"),
        Metric("value1", 10, levels=(30.0, 50.0)),
        Result(state=State.WARN, summary="Value 2: 20.00 (warn/crit at 20.00/50.00)"),
        Metric("value2", 20, levels=(20, 50), boundaries=(0, 100)),
    ]


@pytest.mark.parametrize(
    "string_table_row,item,is_discovered,expected_result",
    [
        pytest.param(
            ["1", "ut_item_name", "metric=0", "Detail"],
            "ut_item_name",
            True,
            [
                Result(state=State.WARN, summary="Detail"),
                Result(state=State.OK, notice="Metric: 0.00"),
                Metric("metric", 0.0),
            ],
            id="all four elements as documented",
        ),
        pytest.param(
            ["1", "ut_item_name", "metric=0"],
            "ut_item_name",
            True,
            [
                Result(state=State.OK, notice="Metric: 0.00"),
                Metric("metric", 0.0),
            ],
            id="missing summary; should not be OK!",  # TODO: this documents a bug, see SUP-17314
        ),
        pytest.param(
            ["1", "ut_item_name", "-"],
            "ut_item_name",
            True,
            [],
            id="empty metric; should not be discovered!",  # TODO: this documents a bug, see SUP-17314
        ),
        pytest.param(
            ["1", "ut_item_name"],
            "Line #1",
            True,
            [],
            id="empty metric",
        ),
        pytest.param(
            ["1"],
            "Line #1",
            True,
            [],
            id="single element",
        ),
        pytest.param(
            ["UT_RANDOM_STRING"],
            "Line #1",
            True,
            [],
            id="single random string",
        ),
    ],
)
def test_check_sub_17314(
    string_table_row: list[str], item: str, is_discovered: bool, expected_result: list[Result]
) -> None:
    assert (
        list(local.check_local("ut_item_name", {}, local.parse_local([string_table_row])))
        == expected_result
    )
    assert list(local.discover_local(local.parse_local([string_table_row]))) == (
        [Service(item=item)] if is_discovered else []
    )


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os

    from tests.testlib.common.repo import repo_path

    assert not pytest.main(
        [
            "--doctest-modules",
            os.path.join(repo_path(), "cmk/plugins/collection/agent_based/local.py"),
        ]
    )
    pytest.main(["-vvsx", __file__])
