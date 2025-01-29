#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, State, StringTable
from cmk.plugins.collection.agent_based.kaspersky_av_tasks import (
    check_kaspersky_av_tasks,
    parse_kaspersky_av_tasks,
    Section,
)


@pytest.mark.parametrize("string_table,expected_result", [([["UnnamedValue:", "Value"]], {})])
def test_parse_kaspersky_av_tasks(string_table: StringTable, expected_result: Section) -> None:
    assert parse_kaspersky_av_tasks(string_table) == expected_result


@pytest.mark.parametrize(
    "item,section,results",
    [
        (
            "System:EventManager",
            {
                "UnmonitoredTask": {"State": "NotStarted"},
                "System:EventManager": {"State": "Started"},
            },
            [Result(state=State.OK, summary="Current state is Started")],
        ),
        (
            "System:EventManager",
            {"System:EventManager": {"State": "NotStarted"}},
            [Result(state=State.CRIT, summary="Current state is NotStarted")],
        ),
        (
            "System:EventManager",
            {},
            [Result(state=State.UNKNOWN, summary="Task not found in agent output")],
        ),
    ],
)
def test_check_kaspersky_av_client(item: str, section: Section, results: CheckResult) -> None:
    assert list(check_kaspersky_av_tasks(item, section)) == results
