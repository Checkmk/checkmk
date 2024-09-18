#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableMapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, render, Result, State


def store_sync_time(
    value_store: MutableMapping[str, Any], sync_time: float, value_store_key: str
) -> None:
    value_store[value_store_key] = sync_time


def _check_time_difference(
    sync_time: float,
    now: float,
    levels_upper: tuple[float, float] | None,
    metric_name: str | None,
    label: str,
    notice_only: bool,
) -> CheckResult:
    time_difference = now - sync_time
    if time_difference < 0:
        yield Result(
            state=State.CRIT,
            summary="Cannot reasonably calculate time since last synchronization "
            "(hosts time is running ahead)",
        )
        return

    yield from check_levels_v1(
        value=time_difference,
        levels_upper=levels_upper,
        metric_name=metric_name,
        render_func=render.timespan,
        label=label,
        notice_only=notice_only,
    )


def tolerance_check(
    *,
    sync_time: float | None,
    levels_upper: tuple[float, float] | None,
    value_store: MutableMapping[str, Any],
    metric_name: str | None,
    label: str,
    value_store_key: str,
    notice_only: bool = False,
) -> CheckResult:
    now = time.time()

    if sync_time is None:
        if (last_sync := value_store.get(value_store_key)) is None:
            store_sync_time(value_store, now, value_store_key)

            if notice_only:
                yield Result(state=State.OK, notice=f"{label}: N/A (started monitoring)")
            else:
                yield Result(state=State.OK, summary=f"{label}: N/A (started monitoring)")
            return

        yield from _check_time_difference(
            last_sync,
            now,
            levels_upper,
            metric_name,
            label,
            notice_only,
        )
    else:
        store_sync_time(value_store, sync_time, value_store_key)
        yield from _check_time_difference(
            sync_time,
            now,
            levels_upper,
            metric_name,
            label,
            notice_only,
        )
