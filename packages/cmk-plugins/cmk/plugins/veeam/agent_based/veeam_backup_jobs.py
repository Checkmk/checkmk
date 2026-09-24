#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class BackupJob:
    """Mirrors the VBR REST API's JobStateModel (GET /api/v1/jobs/states)."""

    job_type: str
    status: str
    last_run: float | None
    last_result: str
    next_run: float | None
    workload: str
    repository_name: str | None
    objects_count: int
    duration: float | None


Section = Mapping[str, BackupJob]

# Veeam's TimeSpan format: "[-][d.]hh:mm:ss[.fffffff]"
_DOTNET_TIMESPAN = re.compile(
    r"^(?:(?P<days>\d+)\.)?(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)(?:\.\d+)?$"
)


def parse_dotnet_timespan_seconds(duration: str) -> float | None:
    if (match := _DOTNET_TIMESPAN.match(duration)) is None:
        return None
    days = int(match["days"] or 0)
    hours, minutes, seconds = int(match["hours"]), int(match["minutes"]), int(match["seconds"])
    return float(((days * 24 + hours) * 60 + minutes) * 60 + seconds)


def parse_iso8601_epoch(value: str) -> float | None:
    """Parses an ISO 8601 timestamp with an explicit UTC offset, e.g.
    "2024-02-04T21:40:34.473+03:00" (the format the VBR REST API uses)."""
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def parse_veeam_backup_jobs(string_table: StringTable) -> Section:
    section: dict[str, BackupJob] = {}
    for line in string_table:
        job_dict = json.loads(line[0])
        session_progress = job_dict.get("sessionProgress") or {}
        duration = session_progress.get("duration")
        last_run = job_dict.get("lastRun")
        next_run = job_dict.get("nextRun")
        section[job_dict["name"]] = BackupJob(
            job_type=job_dict["type"],
            status=job_dict["status"],
            last_run=parse_iso8601_epoch(last_run) if last_run is not None else None,
            last_result=job_dict["lastResult"],
            next_run=parse_iso8601_epoch(next_run) if next_run is not None else None,
            workload=job_dict["workload"],
            repository_name=job_dict.get("repositoryName"),
            objects_count=job_dict["objectsCount"],
            duration=parse_dotnet_timespan_seconds(duration) if duration is not None else None,
        )
    return section


def discovery_veeam_backup_jobs(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def monitoring_state(last_result: str) -> State:
    match last_result:
        case "None":
            # No execution history yet: its first run is still pending.
            return State.OK
        case "Success":
            return State.OK
        case "Failed":
            return State.CRIT
        case "Warning":
            return State.WARN
        case _:
            return State.UNKNOWN


def check_veeam_backup_jobs(item: str, section: Section) -> CheckResult:
    if (job := section.get(item)) is None:
        return

    if job.last_run is None:
        yield Result(state=State.OK, summary="No run has happened yet")
    else:
        yield Result(
            state=monitoring_state(job.last_result),
            summary=f"Status: {job.status}, Result: {job.last_result}",
        )
        yield Result(state=State.OK, summary=f"Last run: {render.datetime(job.last_run)}")

    if job.duration is not None:
        yield Result(state=State.OK, summary=f"Duration: {render.timespan(job.duration)}")
        yield Metric("duration", job.duration)

    if job.next_run is not None:
        yield Result(state=State.OK, summary=f"Next run: {render.datetime(job.next_run)}")

    if job.repository_name is not None:
        yield Result(state=State.OK, summary=f"Target repository: {job.repository_name}")

    yield Result(state=State.OK, summary=f"Objects: {job.objects_count}")
    yield Result(state=State.OK, summary=f"Type: {job.job_type}")


agent_section_veeam_backup_jobs = AgentSection(
    name="veeam_backup_jobs",
    parse_function=parse_veeam_backup_jobs,
    supersedes=["veeam_jobs"],
)

check_plugin_veeam_backup_jobs = CheckPlugin(
    name="veeam_backup_jobs",
    service_name="Backup job %s",
    discovery_function=discovery_veeam_backup_jobs,
    check_function=check_veeam_backup_jobs,
)
