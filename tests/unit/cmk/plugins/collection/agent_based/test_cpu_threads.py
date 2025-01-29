#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.cpu import parse_cpu
from cmk.plugins.collection.agent_based.cpu_threads import check_cpu_threads, discover_cpu_threads
from cmk.plugins.lib.cpu import Load, ProcessorType, Section, Threads


def test_cpu_threads() -> None:
    section = Section(
        load=Load(0.1, 0.1, 0.1),
        num_cpus=4,
        threads=Threads(count=1234),
    )
    params: dict[str, Any] = {}
    result = set(check_cpu_threads(params, section))
    assert result == {
        Metric("threads", 1234.0),
        Result(state=State.OK, summary="1234"),
    }


def test_cpu_threads_max_threads() -> None:
    section = Section(
        load=Load(0.1, 0.1, 0.1),
        num_cpus=4,
        threads=Threads(count=1234, max=2468),
    )
    params: dict[str, Any] = {}
    result = set(check_cpu_threads(params, section))
    assert result == {
        Metric("thread_usage", 50.0),
        Metric("threads", 1234.0),
        Result(state=State.OK, summary="1234"),
        Result(state=State.OK, summary="Usage: 50.00%"),
    }


STRING_TABLE_RELATIVE: StringTable = [
    ["0.88", "0.83", "0.87", "2/1748", "21050", "8"],
    ["124069"],
]


@pytest.mark.parametrize(
    "info, check_result",
    [
        (
            [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]],
            {
                Metric("threads", 2148.0, levels=(2000.0, 4000.0)),
                Result(state=State.WARN, summary="2148 (warn/crit at 2000/4000)"),
            },
        ),
        (
            STRING_TABLE_RELATIVE,
            {
                Metric("threads", 1748.0, levels=(2000.0, 4000.0)),
                Result(state=State.OK, summary="1748"),
                Metric("thread_usage", 1.408893438328672),
                Result(state=State.OK, summary="Usage: 1.41%"),
            },
        ),
    ],
)
def test_cpu_threads_regression(info: StringTable, check_result: CheckResult) -> None:
    section = parse_cpu(info)
    assert section is not None
    params = {"levels": ("levels", (2000, 4000))}
    assert list(discover_cpu_threads(section)) == [Service()]
    assert set(check_cpu_threads(params, section)) == check_result


@pytest.mark.parametrize(
    "params, levels",
    [
        pytest.param(
            {},
            {"thread_usage": (None, None), "threads": (None, None)},
            id="implicitly no levels set",
        ),
        pytest.param(
            {"levels_percent": "no_levels"},
            {"thread_usage": (None, None), "threads": (None, None)},
            id="explicitly unset levels_percent",
        ),
        pytest.param(
            {"levels_percent": ("levels", (10, 20))},
            {"thread_usage": (10.0, 20.0), "threads": (None, None)},
            id="levels set",
        ),
    ],
)
def test_relative_but_no_absolute_levels(
    params,
    levels,
):
    section = parse_cpu(STRING_TABLE_RELATIVE)
    assert section
    found_levels = {}
    for element in check_cpu_threads(params=params, section=section):
        if isinstance(element, Metric):
            found_levels[element.name] = element.levels
    assert found_levels == levels


def test_parse_missing_thread_info():
    # thread info can be missing on an AIX system:
    # $ ps -eo thcount | awk '{SUM+=$1} END {print SUM}'
    #   ps: 0509-001 There is not enough memory available now.
    #    Try again later or
    #    follow local problem reporting procedures.
    assert parse_cpu([["0.88", "0.83", "0.87", "2/", "21050", "8"]]) == Section(
        load=Load(load1=0.88, load5=0.83, load15=0.87),
        num_cpus=8,
        threads=Threads(count=None, max=None),
        type=ProcessorType.unspecified,
    )
