#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from enum import Enum
from typing import Mapping, NamedTuple, Tuple, TypedDict

from .agent_based_api.v1 import check_levels, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


class CDPState(Enum):
    RUNNING = "Running"
    FAILED = "Failed"
    STOPPED = "Stopped"
    UNKNOWN = None


class CDPJob(NamedTuple):
    name: str
    time_diff: float
    state: CDPState


STATE_MAPPING: Mapping[CDPState, state] = {
    CDPState.RUNNING: state.OK,
    CDPState.FAILED: state.CRIT,
    CDPState.STOPPED: state.CRIT,
    CDPState.UNKNOWN: state.UNKNOWN,
}

Section = Mapping[str, CDPJob]


class CheckParams(TypedDict):
    age: Tuple[float, float]


def parse_veeam_cdp_jobs(string_table: type_defs.StringTable) -> Section:
    return {
        name: CDPJob(name, time.time() - float(last_sync), CDPState(state))
        for name, last_sync, state in string_table
    }


register.agent_section(
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
        state=STATE_MAPPING.get(cdp.state, state.UNKNOWN),
        summary=f"State: {cdp.state.value}",
    )
    yield from check_levels(
        value=cdp.time_diff,
        levels_upper=params.get("age"),
        metric_name=None,
        render_func=render.timespan,
        label="Time since last CDP Run",
    )


register.check_plugin(
    name="veeam_cdp_jobs",
    service_name="VEEAM CDP Job %s",
    discovery_function=discovery_veeam_cdp_jobs,
    check_function=check_veeam_cdp_jobs,
    check_ruleset_name="veeam_cdp_jobs",
    check_default_parameters=CheckParams(age=(108000, 172800)),
)
