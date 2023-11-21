#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any
from unittest import mock

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.timesync import store_sync_time, tolerance_check


def test_tolerance_check_set_sync_time() -> None:
    sync_time = 23.0
    value_store: dict[str, Any] = {}

    store_sync_time(value_store, sync_time, value_store_key="time_server")

    assert value_store["time_server"] == sync_time


@mock.patch("time.time", mock.Mock(return_value=100.0))
def test_tolerance_check_new_sync_time() -> None:
    sync_time = 90.0
    value_store: dict[str, Any] = {}
    assert list(
        tolerance_check(
            sync_time=sync_time,
            levels_upper=(0.0, 0.0),
            value_store=value_store,
            metric_name="last_sync_time",
            label="Time since last sync",
            value_store_key="time_server",
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Time since last sync: 10 seconds (warn/crit at 0 seconds/0 seconds)",
        ),
        Metric("last_sync_time", 10.0, levels=(0.0, 0.0)),
    ]
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
@mock.patch("time.time", mock.Mock(return_value=42.0))
def test_tolerance_check_no_last_sync(notice_only: bool, expected_result: Result) -> None:
    value_store: dict[str, Any] = {}
    assert list(
        tolerance_check(
            sync_time=None,
            levels_upper=None,
            value_store=value_store,
            metric_name="last_sync_time",
            label="Time since last sync",
            value_store_key="time_server",
            notice_only=notice_only,
        )
    ) == [expected_result]
    assert value_store["time_server"] == 42.0


@mock.patch("time.time", mock.Mock(return_value=42.0))
def test_host_time_ahead():
    value_store: dict[str, Any] = {"time_server": 43.0}
    assert list(
        tolerance_check(
            sync_time=None,
            levels_upper=None,
            value_store=value_store,
            metric_name="last_sync_time",
            label="Time since last sync",
            value_store_key="time_server",
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Cannot reasonably calculate time since last synchronization (hosts time is running ahead)",
        ),
    ]


@mock.patch("time.time", mock.Mock(return_value=100.0))
def test_tolerance_check_stored_sync_time() -> None:
    sync_time = 90.0
    value_store: dict[str, Any] = {
        "time_server": sync_time,
    }
    assert list(
        tolerance_check(
            sync_time=None,
            levels_upper=(0.0, 0.0),
            value_store=value_store,
            metric_name="last_sync_time",
            label="Time since last sync",
            value_store_key="time_server",
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Time since last sync: 10 seconds (warn/crit at 0 seconds/0 seconds)",
        ),
        Metric("last_sync_time", 10.0, levels=(0.0, 0.0)),
    ]
    assert value_store["time_server"] == sync_time
