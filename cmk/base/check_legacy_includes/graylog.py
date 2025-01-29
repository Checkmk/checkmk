#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import calendar
import json as json_module
import time

from cmk.agent_based.legacy.v0_unstable import check_levels
from cmk.agent_based.v2 import get_average, get_rate, get_value_store, render
from cmk.plugins.lib import graylog

json = json_module
parse_graylog_agent_data = graylog.deserialize_and_merge_json


def handle_iso_utc_to_localtimestamp(iso_8601_time: str) -> int:
    if len(iso_8601_time) == 20:
        time_format = "%Y-%m-%dT%H:%M:%SZ"
    else:
        time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    struc_time = time.strptime(iso_8601_time, time_format)
    local_timestamp = calendar.timegm(struc_time)

    return local_timestamp


def handle_graylog_messages(messages, params):
    msgs_levels_upper = params.get("msgs_upper", (None, None))
    msgs_levels_lower = params.get("msgs_lower", (None, None))

    yield check_levels(
        messages,
        "messages",
        msgs_levels_upper + msgs_levels_lower,
        human_readable_func=int,
        infoname="Total number of messages",
    )

    avg_key = "msgs_avg"
    avg = params.get(avg_key, 30)
    msgs_avg_levels_upper = params.get("msgs_avg_upper", (None, None))
    msgs_avg_levels_lower = params.get("msgs_avg_lower", (None, None))
    this_time = time.time()

    value_store = get_value_store()

    rate = get_rate(
        get_value_store(), "graylog_%s.rate" % avg_key, this_time, messages, raise_overflow=True
    )
    avg_rate = get_average(value_store, f"graylog_{avg_key}.avg", this_time, rate, avg)

    yield check_levels(
        avg_rate,
        avg_key,
        msgs_avg_levels_upper + msgs_avg_levels_lower,
        infoname="Average number of messages (%s)" % render.timespan(avg * 60),
    )

    diff_key = "msgs_diff"
    timespan = params.get(diff_key, 1800)
    diff_levels_upper = params.get("%s_upper" % diff_key, (None, None))
    diff_levels_lower = params.get("%s_lower" % diff_key, (None, None))

    diff = _get_value_diff("graylog_%s" % diff_key, messages, timespan)

    yield check_levels(
        diff,
        "graylog_diff",
        diff_levels_upper + diff_levels_lower,
        human_readable_func=int,
        infoname="Total number of messages since last check (within %s)"
        % render.timespan(timespan),
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
