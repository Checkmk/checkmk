#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class Job:
    type_: str
    last_state: str
    last_result: str
    creation_time: str
    end_time: str


def discovery_veeam_jobs(section: Mapping[str, Job | None]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.keys())


def check_veeam_jobs(item: str, section: Mapping[str, Job | None]) -> CheckResult:
    if (job := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f"State: {job.last_state}")
    if job.last_state in ["Starting", "Working", "Postprocessing"]:
        state = State.OK
    elif job.last_result == "Success":
        state = State.OK
    elif job.last_state == "Idle" and job.type_ == "BackupSync":
        # A sync job is always idle
        state = State.OK
    elif job.last_result == "Failed":
        state = State.CRIT
    elif job.last_state == "Stopped" and job.last_result == "Warning":
        state = State.WARN
    else:
        state = State.UNKNOWN

    yield Result(state=state, summary=f"Result: {job.last_result}")
    yield Result(state=State.OK, summary=f"Creation time: {job.creation_time}")
    yield Result(state=State.OK, summary=f"End time: {job.end_time}")
    yield Result(state=State.OK, summary=f"Type: {job.type_}")


def parse_veeam_jobs(string_table: StringTable) -> Mapping[str, Job | None]:
    section: dict[str, Job | None] = {}
    for line in string_table:
        if len(line) < 6:
            section[line[0]] = None
        else:
            type_, last_state, last_result, creation_time, end_time = line[1:6]
            section[line[0]] = Job(
                type_=type_,
                last_state=last_state,
                last_result=last_result,
                creation_time=creation_time,
                end_time=end_time,
            )
    return section


register.agent_section(
    name="veeam_jobs",
    parse_function=parse_veeam_jobs,
)

register.check_plugin(
    name="veeam_jobs",
    service_name="VEEAM Job %s",
    discovery_function=discovery_veeam_jobs,
    check_function=check_veeam_jobs,
)
