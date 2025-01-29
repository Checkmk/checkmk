#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyResult
from cmk.agent_based.v2 import StringTable

MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS = {
    "stratum": (2, 3),
    "offset": (10, 20),  # us
}


_Levels = tuple[int, int]


def check_mbg_lantime_state_common(
    states: Mapping[str, tuple[int, str]],
    levels_stratum: _Levels,
    levels_offset: _Levels,
    section: StringTable,
) -> Iterable[LegacyResult]:
    ntp_state, stratum, refclock_name, refclock_offset = section[0]

    # Handle State
    yield states[ntp_state][0], "State: " + states[ntp_state][1], []

    # if refclock_offset (and thus also refclock_name) are 'n/a'
    # we must not treat them as numbers or create metrics
    if refclock_offset == "n/a":
        return

    # Check the reported stratum
    yield check_levels(
        int(stratum),
        None,
        params=levels_stratum,
        human_readable_func=lambda x: str(int(x)),
        infoname="Stratum",
    )

    # Add refclock information
    yield 0, "Reference clock: " + refclock_name, []

    # Check offset
    # offset AND levels are measured in microseconds
    # Valuespec of "offset" has unit info: microseconds
    warn, crit = levels_offset
    yield check_levels(
        float(refclock_offset),
        "offset",
        params=(warn, crit, -warn, -crit),
        human_readable_func=lambda x: f"{x:g} µs",
        infoname="Reference clock offset",
    )
