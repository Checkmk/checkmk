#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
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


def monitoring_state(last_state: str, last_result: str, type_: str) -> State:
    if last_result == "None":
        if last_state in ["Starting", "Working", "Postprocessing"]:
            return State.OK
        if last_state == "Idle" and type_ == "BackupSync":
            return State.OK
    if last_result == "Success":
        return State.OK
    if last_result == "Failed":
        return State.CRIT
    if last_result == "Warning":
        return State.WARN
    return State.UNKNOWN


def check_veeam_jobs(item: str, section: Mapping[str, Job | None]) -> CheckResult:
    if (job := section.get(item)) is None:
        return

    yield Result(
        state=monitoring_state(job.last_state, job.last_result, job.type_),
        summary=f"State: {job.last_state}, Result: {job.last_result}",
    )
    if job.creation_time != "":
        yield Result(state=State.OK, summary=f"Creation time: {job.creation_time}")
    if job.end_time != "":
        yield Result(state=State.OK, summary=f"End time: {job.end_time}")
    yield Result(state=State.OK, summary=f"Type: {job.type_}")


def parse_veeam_jobs(string_table: StringTable) -> Mapping[str, Job | None]:
    section: dict[str, Job | None] = {}
    for line in string_table:
        if len(line) < 2:
            section[line[0]] = None
        else:
            # If end_time/creation_time are empty strings, then tab seperators are simply discarded,
            # thus the resulting string_table line has 4 or 5 elements, despite being valid.
            # We reinsert the missing emtpy str by hand.
            type_, last_state, last_result, creation_time, end_time = [*line, "", ""][1:6]
            section[line[0]] = Job(
                type_=type_,
                last_state=last_state,
                last_result=last_result,
                creation_time=creation_time,
                end_time=end_time,
            )
    return section


agent_section_veeam_jobs = AgentSection(
    name="veeam_jobs",
    parse_function=parse_veeam_jobs,
)

check_plugin_veeam_jobs = CheckPlugin(
    name="veeam_jobs",
    service_name="VEEAM Job %s",
    discovery_function=discovery_veeam_jobs,
    check_function=check_veeam_jobs,
)
