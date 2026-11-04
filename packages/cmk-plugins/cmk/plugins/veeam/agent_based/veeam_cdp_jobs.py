#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import NamedTuple, TypedDict

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


class CDPState(Enum):
    INITIAL_SYNC = "InitialSync"
    RUNNING = "Running"
    FAILED = "Failed"
    STOPPED = "Stopped"
    DISABLED = "Disabled"
    UNKNOWN = None


class CDPJob(NamedTuple):
    name: str
    state: CDPState
    raw_state: str
    last_restore_point: float | None
    last_session_result: str | None
    last_session_end: float | None


STATE_MAPPING: Mapping[CDPState, State] = {
    CDPState.INITIAL_SYNC: State.OK,
    CDPState.RUNNING: State.OK,
    CDPState.FAILED: State.CRIT,
    CDPState.STOPPED: State.CRIT,
    CDPState.DISABLED: State.OK,
    CDPState.UNKNOWN: State.UNKNOWN,
}

LAST_RESULT_MAPPING: Mapping[str, State] = {
    "Success": State.OK,
    "Warning": State.WARN,
    "Failed": State.CRIT,
}

Section = Mapping[str, CDPJob]


class CheckParams(TypedDict):
    age: LevelsT[float]


class DiscoveryParams(TypedDict):
    discover_disabled: bool


DEFAULT_DISCOVERY_PARAMETERS = DiscoveryParams(discover_disabled=True)


def _parse_timestamp(raw: str) -> float | None:
    # Some agent outputs may provide lines like:
    # ['"JOB-NAME"', '1695809510,31277', 'Running']
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _parse_state(raw_state: str) -> CDPState:
    try:
        return CDPState(raw_state)
    except ValueError:
        # Veeam may report policy states we do not model. A single unknown value
        # must not render the whole section unparseable.
        return CDPState.UNKNOWN


def _parse_line(line: Sequence[str]) -> CDPJob:
    # The second field used to hold the next run, which CDP policies don't have.
    # Older agent plugins send 3 fields, or 5 with the policy's result, which is always None.
    match line:
        case [name, _next_run, state, last_restore_point, last_session_result, last_session_end]:
            pass
        case [name, _next_run, state, last_restore_point, _policy_result]:
            last_session_result, last_session_end = "null", "null"
        case [name, _next_run, state]:
            last_restore_point, last_session_result, last_session_end = "null", "null", "null"
        case _:
            raise ValueError(line)
    return CDPJob(
        name,
        _parse_state(state),
        state,
        _parse_timestamp(last_restore_point),
        None if last_session_result in ("null", "None", "") else last_session_result,
        _parse_timestamp(last_session_end),
    )


def parse_veeam_cdp_jobs(string_table: StringTable) -> Section:
    return {
        job.name: job
        for job in (_parse_line(line) for line in string_table if len(line) in (3, 5, 6))
    }


agent_section_veeam_cdp_jobs = AgentSection(
    name="veeam_cdp_jobs",
    parse_function=parse_veeam_cdp_jobs,
)


def discovery_veeam_cdp_jobs(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for name, cdp in section.items():
        if params["discover_disabled"] or cdp.state is not CDPState.DISABLED:
            yield Service(item=name)


def check_veeam_cdp_jobs(item: str, params: CheckParams, section: Section) -> CheckResult:
    yield from check_veeam_cdp_jobs_at(item, params, section, time.time())


def check_veeam_cdp_jobs_at(
    item: str, params: CheckParams, section: Section, now: float
) -> CheckResult:
    if not (cdp := section.get(item)):
        return

    yield Result(
        state=STATE_MAPPING.get(cdp.state, State.UNKNOWN),
        summary=f"State: {cdp.raw_state}",
    )

    if cdp.last_session_result is not None:
        text = f"Last session: {cdp.last_session_result}"
        if cdp.last_session_end is not None:
            text += f", ended {render.datetime(cdp.last_session_end)}"
        if cdp.state is CDPState.DISABLED:
            yield Result(state=State.OK, notice=text)
        else:
            yield Result(
                state=LAST_RESULT_MAPPING.get(cdp.last_session_result, State.UNKNOWN),
                summary=text,
            )

    if cdp.last_restore_point is None or cdp.state is CDPState.DISABLED:
        return

    if (age := now - cdp.last_restore_point) < 0:
        yield Result(
            state=State.WARN,
            summary=(
                "The last long-term restore point is in the future. "
                "Please check the clocks of the Veeam server and the Checkmk server."
            ),
        )
        return

    yield from check_levels(
        value=age,
        levels_upper=params["age"],
        metric_name=None,
        render_func=render.timespan,
        label="Time since last long-term restore point",
    )


check_plugin_veeam_cdp_jobs = CheckPlugin(
    name="veeam_cdp_jobs",
    service_name="VEEAM CDP Job %s",
    discovery_function=discovery_veeam_cdp_jobs,
    discovery_ruleset_name="discovery_veeam_cdp_jobs",
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMETERS,
    check_function=check_veeam_cdp_jobs,
    check_ruleset_name="veeam_cdp_jobs",
    check_default_parameters=CheckParams(age=("fixed", (108000.0, 172800.0))),
)
