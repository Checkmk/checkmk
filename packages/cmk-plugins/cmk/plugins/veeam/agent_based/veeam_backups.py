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


@dataclass(frozen=True)
class Unparsable:
    """A value the API sent in an unexpected format, kept so that it can be surfaced
    instead of silently disappearing like an absent one."""

    raw: str

    def as_result_text(self, field_name: str) -> str:
        return f"{field_name}: Unparsable value ({self.raw})"


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
    duration: float | Unparsable | None
    processing_rate: float | Unparsable | None
    end_time: float | Unparsable | None


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


def _parse_processing_rate_bps(processing_rate: str | None) -> float | Unparsable | None:
    if not processing_rate or processing_rate.upper() == "N/A":
        return None
    if (match := _RATE_PATTERN.match(processing_rate)) is None:
        return Unparsable(processing_rate)
    factor = _RATE_UNIT_FACTORS[(match["unit"] or "B").upper()]
    return float(match["value"]) * factor


def _parse_end_time(end_time: str | None) -> float | Unparsable | None:
    if end_time is None:
        return None
    if (epoch := parse_iso8601_epoch(end_time)) is None:
        return Unparsable(end_time)
    return epoch


def _parse_duration(duration: str | None) -> float | Unparsable | None:
    if duration is None:
        return None
    if (parsed := parse_dotnet_timespan_seconds(duration)) is None:
        return Unparsable(duration)
    return parsed


def parse_veeam_backups(string_table: StringTable) -> Section:
    section: dict[str, BackupTask] = {}
    for line in string_table:
        task_dict = json.loads(line[0])
        progress = task_dict.get("progress") or {}
        result = task_dict.get("result") or {}
        duration = progress.get("duration")
        section[sanitize_name(task_dict["jobName"])] = BackupTask(
            state=task_dict["state"],
            result=result.get("result", "None"),
            result_message=result.get("message"),
            total_size=progress.get("processedSize"),
            read_size=progress.get("readSize"),
            transferred_size=progress.get("transferredSize"),
            duration=_parse_duration(duration),
            processing_rate=_parse_processing_rate_bps(progress.get("processingRate")),
            end_time=_parse_end_time(task_dict.get("endTime")),
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


def check_veeam_backups(
    item: str, params: CheckParameters, section: Section, *, now: float
) -> CheckResult:
    if (task := section.get(item)) is None:
        return

    state = monitoring_state(task.state, task.result)
    summary = f"Status: {task.result}"
    if task.result_message:
        summary += f" ({task.result_message})"
    yield Result(state=state, summary=summary)

    if task.state in _TERMINAL_STATES:
        yield from _check_last_backup(task.end_time, params["age"], now)

    size_info = []
    if task.read_size is not None:
        yield Metric("readsize", task.read_size)
        size_info.append(f"read: {render.bytes(task.read_size)}")
    if task.transferred_size is not None:
        yield Metric("transferredsize", task.transferred_size)
        size_info.append(f"transferred: {render.bytes(task.transferred_size)}")
    if task.total_size is not None:
        yield Metric("backup_size", task.total_size)
        size_summary = f"Size: {render.bytes(task.total_size)}"
        if size_info:
            size_summary += f" ({', '.join(size_info)})"
        yield Result(state=State.OK, summary=size_summary)
    elif size_info:
        yield Result(state=State.OK, notice=f"Size ({', '.join(size_info)})")

    if isinstance(task.processing_rate, Unparsable):
        yield Result(
            state=State.OK,
            notice=task.processing_rate.as_result_text("Average speed"),
        )
    elif task.processing_rate is not None:
        yield from check_levels(
            task.processing_rate,
            metric_name="backup_avgspeed",
            render_func=render.iobandwidth,
            label="Average speed",
            notice_only=True,
        )

    if task.state in _TERMINAL_STATES:
        match task.duration:
            case float():
                yield from check_levels(
                    task.duration,
                    metric_name="backup_duration",
                    render_func=render.timespan,
                    label="Duration",
                    notice_only=True,
                )
            case Unparsable():
                yield Result(
                    state=State.OK,
                    notice=task.duration.as_result_text("Duration"),
                )
            case None:
                pass


def _check_last_backup(
    end_time: float | Unparsable | None, levels_upper: LevelsT[float], now: float
) -> CheckResult:
    if end_time is None:
        yield from check_backup_age(None, levels_upper)
    elif isinstance(end_time, Unparsable):
        yield Result(
            state=State.UNKNOWN,
            summary=end_time.as_result_text("End time"),
        )
    elif (age := now - end_time) < 0:
        yield Result(state=State.UNKNOWN, summary="Last backup: end time is in the future")
    else:
        yield from check_backup_age(
            age, levels_upper, label="Last backup age", metric_name="backup_age"
        )


def check_veeam_backups_now(item: str, params: CheckParameters, section: Section) -> CheckResult:
    yield from check_veeam_backups(item, params, section, now=time.time())


agent_section_veeam_backups = AgentSection(
    name="veeam_backups",
    parse_function=parse_veeam_backups,
    supersedes=["veeam_client"],
)

check_plugin_veeam_backups = CheckPlugin(
    name="veeam_backups",
    service_name="Backup %s",
    discovery_function=discovery_veeam_backups,
    check_function=check_veeam_backups_now,
    check_ruleset_name="veeam_backup",
    check_default_parameters=CheckParameters(
        age=("fixed", (108000.0, 172800.0)),  # 30h/2d, as the agent plug-in's VEEAM Client
    ),
)
