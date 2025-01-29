#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from enum import Enum
from typing import NamedTuple, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class CDPState(Enum):
    RUNNING = "Running"
    FAILED = "Failed"
    STOPPED = "Stopped"
    DISABLED = "Disabled"
    UNKNOWN = None


class CDPJob(NamedTuple):
    name: str
    time_diff: float | None
    state: CDPState


STATE_MAPPING: Mapping[CDPState, State] = {
    CDPState.RUNNING: State.OK,
    CDPState.FAILED: State.CRIT,
    CDPState.STOPPED: State.CRIT,
    CDPState.DISABLED: State.OK,
    CDPState.UNKNOWN: State.UNKNOWN,
}

Section = Mapping[str, CDPJob]


class CheckParams(TypedDict):
    age: tuple[float, float]


def parse_veeam_cdp_jobs(string_table: StringTable) -> Section:
    def _sanitize_last_sync(last_sync: str) -> float:
        # Some agent outputs may provide lines like:
        # ['"JOB-NAME"', '1695809510,31277', 'Running']
        return float(last_sync.replace(",", "."))

    return {
        name: CDPJob(
            name,
            None if last_sync == "null" else time.time() - _sanitize_last_sync(last_sync),
            CDPState(state),
        )
        for name, last_sync, state in string_table
    }


agent_section_veeam_cdp_jobs = AgentSection(
    name="veeam_cdp_jobs",
    parse_function=parse_veeam_cdp_jobs,
)


def discovery_veeam_cdp_jobs(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_veeam_cdp_jobs(item: str, params: CheckParams, section: Section) -> CheckResult:
    if not (cdp := section.get(item)):
        return

    yield Result(
        state=STATE_MAPPING.get(cdp.state, State.UNKNOWN),
        summary=f"State: {cdp.state.value}",
    )

    if cdp.time_diff is None:
        return

    if cdp.time_diff < 0:
        warning_message = (
            "The timestamp of the file is in the future. Please investigate your host times"
        )
        yield Result(state=State.WARN, summary=warning_message)
        return

    yield from check_levels_v1(
        value=cdp.time_diff,
        levels_upper=params.get("age"),
        metric_name=None,
        render_func=render.timespan,
        label="Time since last CDP Run",
    )


check_plugin_veeam_cdp_jobs = CheckPlugin(
    name="veeam_cdp_jobs",
    service_name="VEEAM CDP Job %s",
    discovery_function=discovery_veeam_cdp_jobs,
    check_function=check_veeam_cdp_jobs,
    check_ruleset_name="veeam_cdp_jobs",
    check_default_parameters=CheckParams(age=(108000, 172800)),
)
