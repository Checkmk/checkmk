#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import calendar
import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckResult,
    get_average,
    get_rate,
    get_value_store,
    LevelsT,
    render,
    StringTable,
)

GraylogSection = dict[str, Any]


def deserialize_and_merge_json(string_table: StringTable) -> GraylogSection:
    """
    >>> deserialize_and_merge_json([['{"a": 1, "b": 2}'], ['{"b": 3, "c": 4}']])
    {'a': 1, 'b': 3, 'c': 4}
    """
    parsed: GraylogSection = {}

    for line in string_table:
        parsed.update(json.loads(line[0]))

    return parsed


def handle_iso_utc_to_localtimestamp(iso_8601_time: str) -> int:
    if len(iso_8601_time) == 20:
        time_format = "%Y-%m-%dT%H:%M:%SZ"
    else:
        time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    struc_time = time.strptime(iso_8601_time, time_format)
    local_timestamp = calendar.timegm(struc_time)

    return local_timestamp


def v2_levels(levels: tuple[int, int] | float | None) -> LevelsT[int]:
    match levels:
        case tuple((int(w), int(c))):
            return ("fixed", (w, c))
        case None:
            return ("no_levels", None)
        case other:
            raise TypeError(other)


def handle_graylog_messages(
    messages: int | float, params: Mapping[str, tuple[int, int] | float], *, include_diff: bool
) -> CheckResult:
    yield from check_levels(
        messages,
        metric_name="messages",
        levels_upper=v2_levels(params.get("msgs_upper")),
        levels_lower=v2_levels(params.get("msgs_lower")),
        render_func=str,
        label="Total number of messages",
    )

    avg_key = "msgs_avg"
    avg = params.get(avg_key, 30)
    assert isinstance(avg, (int, float))
    this_time = time.time()

    value_store = get_value_store()

    rate = get_rate(
        get_value_store(), "graylog_%s.rate" % avg_key, this_time, messages, raise_overflow=True
    )
    avg_rate = get_average(value_store, f"graylog_{avg_key}.avg", this_time, rate, avg)

    yield from check_levels(
        avg_rate,
        metric_name=avg_key,
        levels_upper=v2_levels(params.get("msgs_avg_upper")),
        levels_lower=v2_levels(params.get("msgs_avg_lower")),
        label="Average number of messages (%s)" % render.timespan(avg * 60),
    )

    if not include_diff:
        return

    diff_key = "msgs_diff"
    timespan = params.get(diff_key, 1800)
    assert isinstance(timespan, (int, float))

    diff = _get_value_diff("graylog_%s" % diff_key, messages, timespan)

    yield from check_levels(
        diff,
        metric_name="graylog_diff",
        levels_upper=v2_levels(params.get("%s_upper" % diff_key)),
        levels_lower=v2_levels(params.get("%s_lower" % diff_key)),
        render_func=str,
        label="Total number of messages since last check (within %s)" % render.timespan(timespan),
    )


def _get_value_diff(diff_name: str, svc_value: float, timespan: float) -> float:
    this_time = time.time()
    value_store = get_value_store()

    # first call: take current value as diff or assume 0.0
    if (old_state := value_store.get(diff_name)) is None:
        diff_val = 0
        value_store[diff_name] = this_time, svc_value
        return diff_val

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = max(this_time - last_time, 0)
    if timedif < float(timespan):
        diff_val = svc_value - last_val
    else:
        diff_val = 0
        value_store[diff_name] = this_time, svc_value

    return diff_val
