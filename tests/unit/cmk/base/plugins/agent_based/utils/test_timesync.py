#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Dict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.timesync import tolerance_check


def test_tolerance_check_set_sync_time() -> None:
    sync_time = 23.0
    value_store: Dict[str, Any] = {}
    assert (
        list(
            tolerance_check(
                set_sync_time=sync_time,
                levels_upper=(0.0, 0.0),
                now=time.time(),
                value_store=value_store,
            )
        )
        == []
    )
    assert value_store["time_server"] == sync_time


@pytest.mark.parametrize(
    "notice_only,expected_result",
    [
        pytest.param(
            False,
            Result(
                state=State.OK,
                summary="Time since last sync: N/A (started monitoring)",
            ),
            id="summary",
        ),
        pytest.param(
            True,
            Result(
                state=State.OK,
                notice="Time since last sync: N/A (started monitoring)",
            ),
            id="notice_only",
        ),
    ],
)
def test_tolerance_check_no_last_sync(notice_only: bool, expected_result: Result) -> None:
    now = 42.0
    value_store: Dict[str, Any] = {}
    assert list(
        tolerance_check(
            set_sync_time=None,
            levels_upper=None,
            now=now,
            value_store=value_store,
            notice_only=notice_only,
        )
    ) == [expected_result]
    assert value_store["time_server"] == now


def test_host_time_ahead():
    now = 42.0
    value_store: Dict[str, Any] = {"time_server": 43.0}
    assert list(
        tolerance_check(
            set_sync_time=None,
            levels_upper=None,
            now=now,
            value_store=value_store,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
        ),
    ]


def test_tolerance_check() -> None:
    value_store: Dict[str, Any] = {
        "time_server": 90.0,
    }
    assert list(
        tolerance_check(
            set_sync_time=None,
            levels_upper=(0.0, 0.0),
            now=100,
            value_store=value_store,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Time since last sync: 10 seconds (warn/crit at 0 seconds/0 seconds)",
        ),
    ]
    assert value_store["time_server"] == 90.0
