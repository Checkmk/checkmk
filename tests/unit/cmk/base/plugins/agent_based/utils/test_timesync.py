#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Dict

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.timesync import tolerance_check


def test_tolerance_check_set_sync_time():
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


def test_tolerance_check_no_last_sync():
    now = 42.0
    value_store: Dict[str, Any] = {}
    assert list(
        tolerance_check(
            set_sync_time=None,
            levels_upper=None,
            now=now,
            value_store=value_store,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Time since last sync: N/A (started monitoring)",
        ),
    ]
    assert value_store["time_server"] == now


def test_tolerance_check():
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
