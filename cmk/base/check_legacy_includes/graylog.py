#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

import calendar
import json
import time

from cmk.base.check_api import (
    check_levels,
    get_age_human_readable,
    get_average,
    get_item_state,
    get_rate,
    set_item_state,
)


def parse_graylog_agent_data(info):
    parsed = {}

    for line in info:
        parsed.update(json.loads(line[0]))

    return parsed


def handle_iso_utc_to_localtimestamp(iso_8601_time):
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

    rate = get_rate("graylog_%s.rate" % avg_key, this_time, messages)
    avg_rate = get_average("graylog_%s.avg" % avg_key, this_time, rate, avg)

    yield check_levels(
        avg_rate,
        avg_key,
        msgs_avg_levels_upper + msgs_avg_levels_lower,
        infoname="Average number of messages (%s)" % get_age_human_readable(avg * 60),
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
        infoname="Total number of messages last %s" % get_age_human_readable(timespan),
    )


def _get_value_diff(diff_name, svc_value, timespan):
    this_time = time.time()
    old_state = get_item_state(diff_name, None)

    # first call: take current value as diff or assume 0.0
    if old_state is None:
        diff_val = 0
        set_item_state(diff_name, (this_time, svc_value))
        return diff_val

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = max(this_time - last_time, 0)
    if timedif < float(timespan):
        diff_val = svc_value - last_val
    else:
        diff_val = 0
        set_item_state(diff_name, (this_time, svc_value))

    return diff_val
