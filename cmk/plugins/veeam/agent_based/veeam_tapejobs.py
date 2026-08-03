#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)

BACKUP_STATE: Mapping[str, State] = {
    "Success": State.OK,
    "Warning": State.WARN,
    "Failed": State.CRIT,
}

_DAY = 3600 * 24

Section = dict[str, dict[str, str]]


def parse_veeam_tapejobs(string_table: StringTable) -> Section:
    parsed: Section = {}
    columns = [s.lower() for s in string_table[0]]

    for line in string_table[1:]:
        if len(line) < len(columns):
            continue

        name = " ".join(line[: -(len(columns) - 1)])
        job_id, last_result, last_state = line[-(len(columns) - 1) :]
        parsed[name] = {
            "job_id": job_id,
            "last_result": last_result,
            "last_state": last_state,
        }

    return parsed


def discover_veeam_tapejobs(section: Section) -> DiscoveryResult:
    yield from (Service(item=job) for job in section)


def check_veeam_tapejobs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    value_store = get_value_store()
    job_id = data["job_id"]
    last_result = data["last_result"]
    last_state = data["last_state"]

    if last_result != "None" or last_state not in ("Working", "Idle"):
        yield Result(
            state=BACKUP_STATE.get(last_result, State.CRIT),
            summary=f"Last backup result: {last_result}",
        )
        yield Result(state=State.OK, summary=f"Last state: {last_state}")
        value_store[f"{job_id}.running_since"] = None
        return

    running_since = value_store.get(f"{job_id}.running_since")
    now = time.time()
    if not running_since:
        running_since = now
        value_store[f"{job_id}.running_since"] = now
    running_time = now - running_since

    yield Result(
        state=State.OK,
        summary=f"Backup in progress since {render.datetime(running_since)} (currently {last_state.lower()})",
    )
    yield from check_levels(
        running_time,
        levels_upper=("fixed", params["levels_upper"]),
        render_func=render.timespan,
        label="Running time",
    )


agent_section_veeam_tapejobs = AgentSection(
    name="veeam_tapejobs",
    parse_function=parse_veeam_tapejobs,
)

check_plugin_veeam_tapejobs = CheckPlugin(
    name="veeam_tapejobs",
    service_name="VEEAM Tape Job %s",
    discovery_function=discover_veeam_tapejobs,
    check_function=check_veeam_tapejobs,
    check_ruleset_name="veeam_tapejobs",
    check_default_parameters={
        "levels_upper": (1 * _DAY, 2 * _DAY),
    },
)
