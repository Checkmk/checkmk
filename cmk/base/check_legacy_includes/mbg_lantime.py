#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS = {
    "stratum": (2, 3),
    "offset": (10, 20),  # us
}


def check_mbg_lantime_state_common(states, _no_item, params, info):
    ntp_state, stratum, refclock_name, refclock_offset = info[0]
    if not isinstance(params, dict):
        params = {
            "stratum": (params[0], params[1]),
            "offset": (params[2], params[3]),
        }

    # Handle State
    yield states[ntp_state][0], "State: " + states[ntp_state][1]

    # Check the reported stratum
    state = 0
    levels_text = ""
    warn, crit = params["stratum"]
    if int(stratum) >= crit:
        state = 2
    elif int(stratum) >= warn:
        state = 1
    if state != 0:
        levels_text = " (warn/crit at %d/%d)" % (warn, crit)
    yield state, f"Stratum: {stratum}{levels_text}"

    # Add refclock information
    yield 0, "Reference clock: " + refclock_name

    # Check offset
    # offset AND levels are measured in microseconds
    # Valuespec of "offset" has unit info: microseconds
    state = 0
    levels_text = ""
    warn, crit = params["offset"]
    refclock_offset = float(refclock_offset)
    pos_refclock_offset = abs(refclock_offset)
    if pos_refclock_offset >= crit:
        state = 2
    elif pos_refclock_offset >= warn:
        state = 1
    if state != 0:
        levels_text = f" (warn/crit at {warn}/{crit} µs)"
    perfdata = [("offset", refclock_offset, warn, crit)]  # all in us
    yield state, f"Reference clock offset: {refclock_offset:g} µs{levels_text}", perfdata
