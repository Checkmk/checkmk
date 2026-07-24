#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import any_of, check_levels, CheckResult, equals, Result, State

DETECT_MBG_LANTIME_NG = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5597.3"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5597.30"),
)

MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS = {
    "stratum": (2, 3),
    "offset": (10, 20),  # us
}


def check_mbg_lantime_state_common(
    states: Mapping[str, tuple[State, str]],
    levels_stratum: tuple[float, float],
    levels_offset: tuple[float, float],
    ntp_state: str,
    stratum: str,
    refclock_name: str,
    refclock_offset: str | float,
) -> CheckResult:
    ntp_state_state, ntp_state_name = states[ntp_state]
    yield Result(state=ntp_state_state, summary=f"State: {ntp_state_name}")

    # if refclock_offset (and thus also refclock_name) are 'n/a'
    # we must not treat them as numbers or create metrics
    if refclock_offset == "n/a":
        return

    # Check the reported stratum
    yield from check_levels(
        int(stratum),
        levels_upper=("fixed", levels_stratum),
        render_func=lambda x: str(int(x)),
        label="Stratum",
    )

    # Add refclock information
    yield Result(state=State.OK, summary=f"Reference clock: {refclock_name}")

    # Check offset
    # offset AND levels are measured in microseconds
    warn, crit = levels_offset
    yield from check_levels(
        float(refclock_offset),
        metric_name="offset",
        levels_upper=("fixed", (warn, crit)),
        levels_lower=("fixed", (-warn, -crit)),
        render_func=lambda x: f"{x:g} µs",
        label="Reference clock offset",
    )
