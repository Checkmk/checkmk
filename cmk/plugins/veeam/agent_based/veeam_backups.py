#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.agent_based.veeam_backup_jobs import (
    parse_dotnet_timespan_seconds,
    parse_iso8601_epoch,
)


@dataclass(frozen=True, kw_only=True)
class BackupTask:
    """Mirrors the VBR REST API's BackupTaskSessionModel (GET /api/v1/taskSessions),
    enriched with the job name the task's session belongs to.

    BackupTaskSessionModel carries no job name or job ID of its own: that link only
    exists on SessionModel (GET /api/v1/sessions), keyed by the task's sessionId. The
    special agent is assumed to resolve it via that join; if it cannot, this section
    cannot be produced for that task, since `item` (the job name) is not optional here.
    """

    state: str
    result: str
    result_message: str | None
    total_size: int | None
    read_size: int | None
    transferred_size: int | None
    duration: str | None
    processing_rate: str | None
    end_time: float | None


Section = Mapping[str, BackupTask]


def parse_veeam_backups(string_table: StringTable) -> Section:
    section: dict[str, BackupTask] = {}
    for line in string_table:
        task_dict = json.loads(line[0])
        progress = task_dict.get("progress") or {}
        result = task_dict.get("result") or {}
        end_time = task_dict.get("endTime")
        section[task_dict["jobName"]] = BackupTask(
            state=task_dict["state"],
            result=result.get("result", "None"),
            result_message=result.get("message"),
            total_size=progress.get("processedSize"),
            read_size=progress.get("readSize"),
            transferred_size=progress.get("transferredSize"),
            duration=progress.get("duration"),
            processing_rate=progress.get("processingRate"),
            end_time=parse_iso8601_epoch(end_time) if end_time is not None else None,
        )
    return section


def discovery_veeam_backups(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


# ESessionState has 11 values; only "Stopped" is unambiguously terminal. Everything
# else is treated as still in progress, per AC: age/duration must not be evaluated
# while a backup is running or pending. Unconfirmed against a real, currently-running
# session; may need refining once one can be observed.
_TERMINAL_STATES = ("Stopped",)


def monitoring_state(state: str, result: str) -> State:
    match result:
        case "None":
            if state not in _TERMINAL_STATES:
                raise IgnoreResultsError("Data not present at the moment")
            return State.UNKNOWN
        case "Success":
            return State.OK
        case "Failed":
            return State.CRIT
        case "Warning":
            return State.WARN
        case _:
            return State.UNKNOWN


def _parse_processing_rate_bps(processing_rate: str) -> float | None:
    # TODO: confirm the real format/unit of processingRate against actual API traffic.
    # Only the case where it's a plain byte count is handled; anything else is shown
    # as text without a metric.
    try:
        return float(processing_rate)
    except ValueError:
        return None


def check_veeam_backups(item: str, section: Section) -> CheckResult:
    if (task := section.get(item)) is None:
        return

    state = monitoring_state(task.state, task.result)
    summary = f"Status: {task.result}"
    if task.result_message:
        summary += f" ({task.result_message})"
    yield Result(state=state, summary=summary)

    size_info = []
    if task.total_size is not None:
        yield Metric("totalsize", task.total_size)
        size_info.append(f"total: {render.bytes(task.total_size)}")
    if task.read_size is not None:
        yield Metric("readsize", task.read_size)
        size_info.append(f"read: {render.bytes(task.read_size)}")
    if task.transferred_size is not None:
        yield Metric("transferredsize", task.transferred_size)
        size_info.append(f"transferred: {render.bytes(task.transferred_size)}")
    if size_info:
        yield Result(
            state=State.OK,
            summary=f"Size ({', '.join(size_info)})",
        )

    if task.processing_rate is not None:
        if (rate_bps := _parse_processing_rate_bps(task.processing_rate)) is not None:
            yield from check_levels(
                rate_bps,
                metric_name="avgspeed",
                render_func=render.iobandwidth,
                label="Average speed",
            )
        else:
            # TODO: confirm whether this branch is ever actually reachable once we can
            # test against real API responses. If it is, move the parsing into the
            # parse function instead of guessing here.
            yield Result(
                state=State.OK,
                summary=f"FAILED TO PARSE -> Average speed: ({task.processing_rate})",
            )

    if task.state in _TERMINAL_STATES:
        if task.duration is not None:
            if (duration_seconds := parse_dotnet_timespan_seconds(task.duration)) is not None:
                yield from check_levels(
                    duration_seconds,
                    metric_name="duration",
                    render_func=render.timespan,
                    label="Duration",
                )
            else:
                # TODO: confirm whether this branch is ever actually reachable once we
                # can test against real API responses. If it is, move the parsing into
                # the parse function instead of guessing here.
                yield Result(
                    state=State.OK,
                    summary=f"FAILED TO PARSE -> Duration: ({task.duration})",
                )

        if task.end_time is not None:
            age = time.time() - task.end_time
            if age < 0:
                yield Result(
                    state=State.UNKNOWN,
                    summary="Last backup: end time is in the future",
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"Last backup: {render.timespan(age)} ago",
                )


agent_section_veeam_backups = AgentSection(
    name="veeam_backups",
    parse_function=parse_veeam_backups,
    supersedes=["veeam_client"],
)

check_plugin_veeam_backups = CheckPlugin(
    name="veeam_backups",
    service_name="Backup %s",
    discovery_function=discovery_veeam_backups,
    check_function=check_veeam_backups,
)
