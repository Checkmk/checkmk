#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import veeam_cdp_jobs

DATA = [
    ["Test 1", "1632216559.73749", "Running"],
    ["Test 2", "1632216559.87806", "Failed"],
    ["Test 3", "1632216559.87806", "Stopped"],
    ["Test 4", "null", "Disabled"],
    ["Test 5", "1632216559,73749", "Running"],
    ["Test 6", "1632217660", "Running"],
]


@pytest.mark.parametrize(
    "data, result",
    [
        (
            DATA,
            [
                Service(item="Test 1"),
                Service(item="Test 2"),
                Service(item="Test 3"),
                Service(item="Test 4"),
                Service(item="Test 5"),
                Service(item="Test 6"),
            ],
        ),
    ],
)
def test_veeam_cdp_jobs_discovery(
    data: StringTable,
    result: DiscoveryResult,
) -> None:
    section = veeam_cdp_jobs.parse_veeam_cdp_jobs(data)
    assert list(veeam_cdp_jobs.discovery_veeam_cdp_jobs(section)) == result


@pytest.mark.parametrize(
    "item, params, data, result",
    [
        (
            "Test 1",
            veeam_cdp_jobs.CheckParams(age=(108000, 172800)),
            DATA,
            [
                Result(state=State.OK, summary="State: Running"),
                Result(state=State.OK, summary="Time since last CDP Run: 1 minute 40 seconds"),
            ],
        ),
        (
            "Test 2",
            veeam_cdp_jobs.CheckParams(age=(100, 300)),
            DATA,
            [
                Result(state=State.CRIT, summary="State: Failed"),
                Result(
                    state=State.WARN,
                    summary="Time since last CDP Run: 1 minute 40 seconds (warn/crit at 1 minute 40 seconds/5 minutes 0 seconds)",
                ),
            ],
        ),
        (
            "Test 3",
            veeam_cdp_jobs.CheckParams(age=(60, 80)),
            DATA,
            [
                Result(state=State.CRIT, summary="State: Stopped"),
                Result(
                    state=State.CRIT,
                    summary="Time since last CDP Run: 1 minute 40 seconds (warn/crit at 1 minute 0 seconds/1 minute 20 seconds)",
                ),
            ],
        ),
        (
            "Test 4",
            veeam_cdp_jobs.CheckParams(age=(60, 80)),
            DATA,
            [
                Result(state=State.OK, summary="State: Disabled"),
            ],
        ),
        (
            "Test 5",
            veeam_cdp_jobs.CheckParams(age=(108000, 172800)),
            DATA,
            [
                Result(state=State.OK, summary="State: Running"),
                Result(state=State.OK, summary="Time since last CDP Run: 1 minute 40 seconds"),
            ],
        ),
        pytest.param(
            "Test 6",
            veeam_cdp_jobs.CheckParams(age=(108000, 172800)),
            DATA,
            [
                Result(state=State.OK, summary="State: Running"),
                Result(
                    state=State.WARN,
                    summary="The timestamp of the file is in the future. Please investigate your host times",
                ),
            ],
            id="last sync time from the future",
        ),
    ],
)
def test_veeam_cdp_jobs_check(
    item: str,
    params: veeam_cdp_jobs.CheckParams,
    data: StringTable,
    result: CheckResult,
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1632216660, tz=ZoneInfo("UTC"))):
        section = veeam_cdp_jobs.parse_veeam_cdp_jobs(data)
        assert list(veeam_cdp_jobs.check_veeam_cdp_jobs(item, params, section)) == result
