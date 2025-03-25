#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.collection.agent_based import kaspersky_av_client


@pytest.fixture(scope="module", autouse=True)
def set_fixed_timezone():
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))):
        yield


@pytest.mark.parametrize(
    "string_table,now,expected_section",
    [
        (
            [["Fullscan", "01.01.1970", "00:00:00", "1"]],
            1,
            {"fullscan_age": 1, "fullscan_failed": True},
        ),
        ([["Signatures", "01.01.1970", "00:00:00"]], 1, {"signature_age": 1}),
        ([["Signatures", "01.01.1970"]], 1, {"signature_age": 1}),
        ([["Signatures", "Missing"]], 0, {}),
    ],
)
def test_parse_kaspersky_av_client(
    string_table: StringTable, now: int, expected_section: kaspersky_av_client.Section
) -> None:
    assert kaspersky_av_client._parse_kaspersky_av_client(string_table, now=now) == expected_section


@pytest.mark.parametrize(
    "section,results",
    [
        (
            {"fullscan_age": 2.3549888134, "signature_age": 2.3549888134},
            [
                Result(
                    state=State.WARN,
                    summary="Last update of signatures: 2 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
                Result(
                    state=State.WARN,
                    summary="Last fullscan: 2 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
            ],
        ),
        (
            {"fullscan_age": 3.35498881343, "signature_age": 3.3549888134},
            [
                Result(
                    state=State.CRIT,
                    summary="Last update of signatures: 3 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
                Result(
                    state=State.CRIT,
                    summary="Last fullscan: 3 seconds ago (warn/crit at 2 seconds ago/3 seconds ago)",
                ),
            ],
        ),
        (
            {"fullscan_failed": True, "fullscan_age": 1.3549888134, "signature_age": 1.3549888134},
            [
                Result(state=State.OK, summary="Last update of signatures: 1 second ago"),
                Result(state=State.OK, summary="Last fullscan: 1 second ago"),
                Result(state=State.CRIT, summary="Last fullscan failed"),
            ],
        ),
        (
            {},
            [
                Result(state=State.UNKNOWN, summary="Last update of signatures unkown"),
                Result(state=State.UNKNOWN, summary="Last fullscan unkown"),
            ],
        ),
    ],
)
def test_check_kaskpersky_av_client(
    section: kaspersky_av_client.Section, results: Sequence[Result]
) -> None:
    test_params = {"signature_age": (2, 3), "fullscan_age": (2, 3)}
    assert list(kaspersky_av_client.check_kaspersky_av_client(test_params, section)) == results
