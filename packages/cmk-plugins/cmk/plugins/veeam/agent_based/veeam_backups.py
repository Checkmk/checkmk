#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
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
    IgnoreResultsError,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.lib import (
    check_backup_age,
    parse_dotnet_timespan_seconds,
    parse_iso8601_epoch,
    sanitize_name,
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
    duration: float | None
    processing_rate: float | None
    processing_rate_raw: str | None
    """The unparsed `processingRate` string, kept so an unexpected format (as opposed
    to the expected "N/A") can still be surfaced instead of silently disappearing."""
    end_time: str | None


Section = Mapping[str, BackupTask]


class CheckParameters(TypedDict):
    age: LevelsT[float]


_RATE_PATTERN = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[KMGTP]?B)?(?:/s)?\s*$", re.IGNORECASE
)

# TODO: confirm the real format and unit base of processingRate against actual API
# traffic. Decimal (SI) prefixes are assumed here (the API's "MB" = 10^6); if the
# field actually uses binary units (MB = 2^20) instead, every parsed rate is about
# 4.6% too low. Neither base is confirmed yet.
_RATE_UNIT_FACTORS = {
    "B": 1,
    "KB": 1_000,
    "MB": 1_000_000,
    "GB": 1_000_000_000,
    "TB": 1_000_000_000_000,
    "PB": 1_000_000_000_000_000,
}


def _parse_processing_rate_bps(processing_rate: str | None) -> float | None:
    if processing_rate is None or (match := _RATE_PATTERN.match(processing_rate)) is None:
        return None
    factor = _RATE_UNIT_FACTORS[(match["unit"] or "B").upper()]
    return float(match["value"]) * factor


def parse_veeam_backups(string_table: StringTable) -> Section:
    section: dict[str, BackupTask] = {}
    for line in string_table:
        task_dict = json.loads(line[0])
        progress = task_dict.get("progress") or {}
        result = task_dict.get("result") or {}
        duration = progress.get("duration")
        processing_rate_raw = progress.get("processingRate")
        section[sanitize_name(task_dict["jobName"])] = BackupTask(
            state=task_dict["state"],
            result=result.get("result", "None"),
            result_message=result.get("message"),
            total_size=progress.get("processedSize"),
            read_size=progress.get("readSize"),
            transferred_size=progress.get("transferredSize"),
            duration=parse_dotnet_timespan_seconds(duration) if duration is not None else None,
            processing_rate=_parse_processing_rate_bps(processing_rate_raw),
            processing_rate_raw=processing_rate_raw,
            end_time=task_dict.get("endTime"),
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


def check_veeam_backups(item: str, params: CheckParameters, section: Section) -> CheckResult:
    if (task := section.get(item)) is None:
        return

    state = monitoring_state(task.state, task.result)
    summary = f"Status: {task.result}"
    if task.result_message:
        summary += f" ({task.result_message})"
    yield Result(state=state, summary=summary)

    size_info = []
    if task.total_size is not None:
        yield Metric("backup_size", task.total_size)
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
        yield from check_levels(
            task.processing_rate,
            metric_name="backup_avgspeed",
            render_func=render.iobandwidth,
            label="Average speed",
        )
    elif task.processing_rate_raw and task.processing_rate_raw.upper() != "N/A":
        yield Result(
            state=State.OK,
            notice=f"Average speed: unparsable value ({task.processing_rate_raw})",
        )

    if task.state in _TERMINAL_STATES:
        if task.duration is not None:
            yield from check_levels(
                task.duration,
                metric_name="backup_duration",
                render_func=render.timespan,
                label="Duration",
            )

        if task.end_time is None:
            yield from check_backup_age(None, params["age"])
        elif (end_time := parse_iso8601_epoch(task.end_time)) is None:
            # TODO: confirm whether this branch is ever actually reachable once we can
            # test against real API responses. If it is, move the parsing into the
            # parse function instead of guessing here.
            yield Result(
                state=State.UNKNOWN,
                summary=f"FAILED TO PARSE -> End time: ({task.end_time})",
            )
        elif (age := time.time() - end_time) < 0:
            yield Result(state=State.UNKNOWN, summary="Last backup: end time is in the future")
        else:
            yield from check_backup_age(age, params["age"])


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
    check_ruleset_name="veeam_backup",
    check_default_parameters=CheckParameters(
        age=("fixed", (108000.0, 172800.0)),  # 30h/2d, as the agent plug-in's VEEAM Client
    ),
)
