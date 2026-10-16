#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.lib import parse_dotnet_timespan_seconds, parse_iso8601_epoch, sanitize_name


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


class DiscoveryParams(TypedDict):
    discover_disabled: bool


DEFAULT_DISCOVERY_PARAMETERS = DiscoveryParams(discover_disabled=True)


class CheckParameters(TypedDict):
    disabled_state: int
    age: LevelsT[float]


DEFAULT_PARAMETERS = CheckParameters(disabled_state=State.OK.value, age=("no_levels", None))


def parse_veeam_backup_jobs(string_table: StringTable) -> Section:
    section: dict[str, BackupJob] = {}
    for line in string_table:
        job_dict = json.loads(line[0])
        session_progress = job_dict.get("sessionProgress") or {}
        duration = session_progress.get("duration")
        last_run = job_dict.get("lastRun")
        next_run = job_dict.get("nextRun")
        section[sanitize_name(job_dict["name"])] = BackupJob(
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


def discovery_veeam_backup_jobs(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for item, job in section.items():
        if params["discover_disabled"] or job.status != "Disabled":
            yield Service(item=item)


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


def check_veeam_backup_jobs(
    item: str,
    params: CheckParameters,
    section: Section,
    *,
    now: float,
) -> CheckResult:
    if (job := section.get(item)) is None:
        return

    status = f"Status: {job.status}, " if job.status in ("Running", "Disabled") else ""
    is_disabled = job.status == "Disabled"
    if job.last_run is None:
        yield Result(
            state=State(params["disabled_state"]) if is_disabled else State.OK,
            summary=f"{status}No run has happened yet",
        )
    else:
        yield Result(
            state=(
                State(params["disabled_state"])
                if is_disabled
                else monitoring_state(job.last_result)
            ),
            summary=f"{status}Result: {job.last_result}",
        )
        if (age := now - job.last_run) < 0:
            yield Result(state=State.OK, summary="Last run: in the future")
        else:
            yield from check_levels(
                age,
                # The state of a disabled job is set by disabled_state alone
                levels_upper=None if is_disabled else params["age"],
                metric_name="veeam_backup_job_age",
                render_func=render.timespan,
                label="Time since last run",
            )
        yield Result(state=State.OK, notice=f"Last run time: {render.datetime(job.last_run)}")

    if not status:
        yield Result(state=State.OK, notice=f"Status: {job.status}")

    if job.duration is not None:
        yield Result(state=State.OK, notice=f"Duration: {render.timespan(job.duration)}")
        yield Metric("backup_duration", job.duration)

    if job.next_run is not None:
        yield Result(state=State.OK, notice=f"Next run: {render.datetime(job.next_run)}")

    if job.repository_name is not None:
        yield Result(state=State.OK, notice=f"Target repository: {job.repository_name}")

    yield Result(state=State.OK, notice=f"Objects: {job.objects_count}")
    yield Metric("veeam_backup_job_objects", job.objects_count)
    yield Result(state=State.OK, notice=f"Type: {job.job_type}")


def check_veeam_backup_jobs_now(
    item: str,
    params: CheckParameters,
    section: Section,
) -> CheckResult:
    yield from check_veeam_backup_jobs(item, params, section, now=time.time())


agent_section_veeam_backup_jobs = AgentSection(
    name="veeam_backup_jobs",
    parse_function=parse_veeam_backup_jobs,
    supersedes=["veeam_jobs"],
)

check_plugin_veeam_backup_jobs = CheckPlugin(
    name="veeam_backup_jobs",
    service_name="Backup job %s",
    discovery_function=discovery_veeam_backup_jobs,
    discovery_ruleset_name="discovery_veeam_backup_jobs",
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMETERS,
    check_function=check_veeam_backup_jobs_now,
    check_ruleset_name="veeam_backup_jobs",
    check_default_parameters=DEFAULT_PARAMETERS,
)
