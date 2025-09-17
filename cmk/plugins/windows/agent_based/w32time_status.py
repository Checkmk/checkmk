#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Useful: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/f60ebce0-df96-4c96-b40b-fdbd34a2c936
# (W32TIME_STATUS_INFO docs... provides some technical insight into what `w32tm` is showing.)

# Example output from agent (but note all strings and numbers are localized):
# <<<w32time_status:sep(0)>>>
# Leap Indicator: 0(no warning)
# Stratum: 4 (secondary reference - syncd by (S)NTP)
# Precision: -23 (119.209ns per tick)
# Root Delay: 0.0154902s
# Root Dispersion: 7.7773722s
# ReferenceId: 0x14653909 (source IP:  20.101.57.9)
# Last Successful Sync Time: 9/11/2025 2:32:05 PM
# Source: time.windows.com,0x9
# Poll Interval: 10 (1024s)
#
# Phase Offset: -0.0038147s
# ClockRate: 0.0156250s
# State Machine: 1 (Hold)
# Time Source Flags: 0 (None)
# Server Role: 0 (None)
# Last Sync Error: 2 (The computer did not resync because only stale time data was available.)
# Time since Last Good Sync Time: 2820.1997480s


# Example with service started but not yet synced
# <<<w32time_status:sep(0)>>>
# Leap Indicator: 3(not synchronized)
# Stratum: 0 (unspecified)
# Precision: -23 (119.209ns per tick)
# Root Delay: 0.0000000s
# Root Dispersion: 0.0000000s
# ReferenceId: 0x00000000 (unspecified)
# Last Successful Sync Time: unspecified
# Source: Local CMOS Clock
# Poll Interval: 10 (1024s)
#
# Phase Offset: 0.0000000s
# ClockRate: 0.0156250s
# State Machine: 0 (Unset)
# Time Source Flags: 0 (None)
# Server Role: 0 (None)
# Last Sync Error: 1 (The computer did not resync because no time data was available.)
# Time since Last Good Sync Time: 10.0402148s

import itertools
import re
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class StateParams(TypedDict):
    never_synced: int
    no_data: int
    stale_data: int
    time_diff_too_large: int
    shutting_down: int


class Params(TypedDict):
    offset: LevelsT[float]
    time_since_last_successful_sync: LevelsT[float]
    states: StateParams


DEFAULT_PARAMS = Params(
    offset=("no_levels", None),
    time_since_last_successful_sync=("no_levels", None),
    states=StateParams(
        never_synced=int(State.OK),
        no_data=int(State.OK),
        stale_data=int(State.OK),
        time_diff_too_large=int(State.OK),
        shutting_down=int(State.OK),
    ),
)


@dataclass(frozen=True, kw_only=True)
class QueryStatus:
    leap_indicator: int
    stratum: int
    precision: int
    root_delay: float
    root_dispersion: float
    reference_id: int  # is source IP useful too?
    last_successful_sync_time: str
    source: str  # flags might be useful
    poll_interval: int
    phase_offset: float
    clock_rate: float
    state_machine: int
    time_source_flags: int
    server_role: int
    last_sync_error: int
    seconds_since_last_good_sync: float


def _parse_int(value: str) -> int:
    value = value.replace("s", "")
    return int(value)


def _parse_float(value: str) -> float:
    value = value.replace("s", "")
    return float(value)


def _parse_hex(value: str) -> int:
    value = value.replace("s", "")
    return int(value, 16)


def _before_parens(value: str) -> str:
    return "".join(itertools.takewhile(lambda c: c != "(", value)).strip()


def _in_parens(value: str) -> str:
    m = re.search(r"\(([^)]*)\)", value)
    return m.group(1) if m else ""


def parse_w32time_status(string_table: StringTable) -> QueryStatus:
    # Hack, in some languages (e.g. German) some lines may run long and wrap
    # If there is no ":" to split on, just drop the lines. In theory this isn't
    # really enough, because a partial line could probably have a ":" in it. In
    # practice and testing, it has been fine.
    string_table = [s for s in string_table if ":" in s[0]]

    # Important that we split on ":" and not ": " as some languages have some lines without a space.
    lines = [s[0].split(":", 1)[1].strip() for s in string_table]

    # Some of these are probably not useful and can go away.
    query_status = QueryStatus(
        leap_indicator=_parse_int(_before_parens(lines[0])),
        stratum=_parse_int(_before_parens(lines[1])),
        precision=_parse_int(_before_parens(lines[2])),
        root_delay=_parse_float(_before_parens(lines[3])),
        root_dispersion=_parse_float(_before_parens(lines[4])),
        reference_id=_parse_hex(_before_parens(lines[5])),
        last_successful_sync_time=lines[6],  # Not super useful, i18n
        source=lines[7],
        poll_interval=_parse_int(_in_parens(lines[8])),
        phase_offset=_parse_float(lines[9]),
        clock_rate=_parse_float(lines[10]),
        state_machine=_parse_int(_before_parens(lines[11])),
        time_source_flags=_parse_int(_before_parens(lines[12])),
        server_role=_parse_int(_before_parens(lines[13])),
        last_sync_error=_parse_int(_before_parens(lines[14])),
        seconds_since_last_good_sync=_parse_float(lines[15]),
    )
    return query_status


agent_section_w32time_status = AgentSection(
    name="w32time_status",
    parse_function=parse_w32time_status,
)


def discover_w32time_status(section: QueryStatus) -> DiscoveryResult:
    yield Service()


def _sync_result_to_check_result(state_params: StateParams, result: int) -> CheckResult:
    match result:
        case 0:
            yield Result(state=State.OK, notice="Sync status: successful")
        case 1:
            yield Result(
                state=State(state_params["no_data"]),
                notice="Sync status: No data from time provider",
            )
        case 2:
            yield Result(
                state=State(state_params["stale_data"]),
                notice="Sync status: Stale data received from time provider",
            )
        case 3:
            yield Result(
                state=State(state_params["time_diff_too_large"]),
                notice="Sync status: Difference in time from provider was too large",
            )
        case 4:
            yield Result(
                state=State(state_params["shutting_down"]),
                notice="Sync status: Time service shutting down",
            )
        case _:
            yield Result(state=State.UNKNOWN, notice="Sync status: Unexpected sync result")


def check_w32time_status(params: Params, section: QueryStatus) -> CheckResult:
    if section.state_machine == 0 and section.reference_id == 0:
        yield Result(
            state=State(params["states"]["never_synced"]),
            summary="Never synchronized (w32tm reported reference ID and state machine both 0)",
        )
        return

    # The levels are inverted for the lower bound, i.e. "more than 500ms" really means
    # "more than 500ms or less than -500ms"
    levels_lower: LevelsT[float] | None = None
    if params["offset"][0] == "fixed":
        levels_lower = ("fixed", (-params["offset"][1][0], -params["offset"][1][1]))

    yield from check_levels(
        value=section.phase_offset,
        metric_name="time_offset",
        levels_upper=params["offset"],
        levels_lower=levels_lower,
        render_func=render.time_offset,
        label="Offset",
    )

    yield from check_levels(
        value=section.seconds_since_last_good_sync,
        levels_upper=params["time_since_last_successful_sync"],
        render_func=lambda s: f"{render.timespan(s)} ago",
        label="Last successful sync",
    )

    # TODO: We split off and ignore the source flags here, but maybe they are useful to report?
    yield Result(state=State.OK, summary=f"Source: {section.source.split(',')[0]}")

    yield from check_levels(
        value=section.root_dispersion,
        metric_name="root_dispersion",
        notice_only=True,
        render_func=render.timespan,
        label="Root dispersion",
    )

    yield from check_levels(
        value=section.root_delay,
        metric_name="root_delay",
        notice_only=True,
        render_func=render.timespan,
        label="Root delay",
    )

    yield from check_levels(
        value=section.stratum,
        notice_only=True,
        label="Stratum",
        render_func=str,
    )

    yield from _sync_result_to_check_result(params["states"], section.last_sync_error)


check_plugin_w32time_status = CheckPlugin(
    name="w32time_status",
    service_name="Windows time service",
    discovery_function=discover_w32time_status,
    check_ruleset_name="w32time_status",
    check_default_parameters=DEFAULT_PARAMS,
    check_function=check_w32time_status,
)
