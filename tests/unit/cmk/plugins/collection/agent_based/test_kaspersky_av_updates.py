#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, State, StringTable
from cmk.plugins.collection.agent_based.kaspersky_av_updates import (
    check_kaspersky_av_updates,
    parse_kaspersky_av_updates,
    Section,
)


@pytest.mark.parametrize(
    "string_table,expected_section",
    [
        ([["single_field", "value"]], {"single_field": "value"}),
        ([["joined_field", "1970-01-01 00", "00", "00"]], {"joined_field": "1970-01-01 00:00:00"}),
        ([["stripped_field", "  stripped   "]], {"stripped_field": "stripped"}),
    ],
)
def test_parse_kaspersky_av_updates(string_table: StringTable, expected_section: Section) -> None:
    assert parse_kaspersky_av_updates(string_table) == expected_section


@pytest.mark.parametrize(
    "section,results",
    [
        (
            {
                "Current AV databases state": "UpToDate",
                "Current AV databases date": "1970-01-01 00:00:00",
                "Last AV databases update date": "1970-01-01 01:00:00",
            },
            [
                Result(state=State.OK, summary="Database State: UpToDate"),
                Result(state=State.OK, summary="Database Date: 1970-01-01 00:00:00"),
                Result(state=State.OK, summary="Last Update: 1970-01-01 01:00:00"),
            ],
        ),
        (
            {
                "Current AV databases state": "NotUpToDate",
                "Current AV databases date": "1970-01-01 00:00:00",
                "Last AV databases update date": "1970-01-01 01:00:00",
            },
            [
                Result(state=State.CRIT, summary="Database State: NotUpToDate"),
                Result(state=State.OK, summary="Database Date: 1970-01-01 00:00:00"),
                Result(state=State.OK, summary="Last Update: 1970-01-01 01:00:00"),
            ],
        ),
    ],
)
def test_check_kaskpersky_av_updates(section: Section, results: CheckResult) -> None:
    assert list(check_kaspersky_av_updates(section)) == results
