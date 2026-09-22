#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
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

SENTINEL_STOPTIME_RUNNING = -1.0


class Status(StrEnum):
    SUCCESS = "Success"
    WARNING = "Warning"
    FAILED = "Failed"
    IN_PROGRESS = "InProgress"
    PENDING = "Pending"

    @classmethod
    def from_str(cls, v: str) -> Status | None:
        try:
            return cls(v)
        except ValueError:
            return None

    def as_state(self) -> State:
        match self:
            case self.WARNING:
                return State.WARN
            case self.FAILED:
                return State.CRIT
            case _:
                return State.OK

    def is_running(self) -> bool:
        return self in [self.IN_PROGRESS, self.PENDING]


@dataclass
class VeeamClient:
    job_name: str
    raw_status: str | None
    total_size_byte: int | None
    read_size_byte: int | None
    transferred_size_byte: int | None
    start_time: datetime | None
    last_backup_age: float | None
    duration: int | None
    avg_speed_bps: int | None
    display_name: str | None
    backup_server: str | None

    @property
    def status(self) -> Status | None:
        return Status.from_str(self.raw_status) if self.raw_status is not None else None


Section = dict[str, VeeamClient]


class CheckParameters(TypedDict):
    age: LevelsT[float]


def _parse_int(raw: str | None) -> int | None:
    """Fields may be absent or empty if Veeam did not report a value."""
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_duration(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        days, hours, minutes, seconds = (int(part) for part in raw.split(":"))
    except ValueError:
        return None
    return seconds + minutes * 60 + hours * 3600 + days * 86400


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%d.%m.%Y %H:%M:%S")


def _parse_stop_time(raw: str | None) -> float | None:
    if raw == "01.01.1900 00:00:00":
        # Backward compatible hack
        return SENTINEL_STOPTIME_RUNNING
    if raw is None:
        return None
    try:
        return time.time() - time.mktime(time.strptime(raw, "%d.%m.%Y %H:%M:%S"))
    except ValueError:
        return None


_KEY_MAPPING: Mapping[str, str] = {
    "Status": "status",
    "JobName": "job_name",
    "TotalSizeByte": "total_size_byte",
    "ReadSizeByte": "read_size_byte",
    "TransferedSizeByte": "transferred_size_byte",
    "StartTime": "start_time",
    "StopTime": "StopTime",
    "LastBackupAge": "last_backup_age",
    "DurationDDHHMMSS": "duration",
    "AvgSpeedBps": "avg_speed_bps",
    "DisplayName": "display_name",
    "BackupServer": "backup_server",
}


def _normalize_line(line: list[str]) -> tuple[str, str | None] | None:
    try:
        key = _KEY_MAPPING[line[0]]
    except KeyError:
        return None
    return key, line[1] if len(line) == 2 else None


def _iter_records(string_table: StringTable) -> Iterator[list[list[str]]]:
    # The agent emits one record per job, always starting with a "Status" line.
    # Splitting on that boundary - instead of assuming a fixed number of lines -
    # keeps the parser working when the set of emitted keys changes between agent
    # versions (e.g. StopTime was replaced by LastBackupAge in 2.5.0).
    record: list[list[str]] | None = None
    for line in string_table:
        if line[0] == "Status":
            if record is not None:
                yield record
            record = []
        if record is not None:
            record.append(line)
    if record is not None:
        yield record


def parse_veeam_client(string_table: StringTable) -> Section:
    data: Section = {}
    for record in _iter_records(string_table):
        chunk_data = dict(
            pair for pair in (_normalize_line(line) for line in record) if pair is not None
        )
        # StopTime is kept for compatibility with old agent versions that reported
        # StopTime instead of LastBackupAge.
        last_backup_age = _parse_float(chunk_data.get("last_backup_age"))
        try:
            age_from_stop_time = _parse_stop_time(chunk_data.pop("StopTime"))
        except KeyError:
            pass
        else:
            if last_backup_age is None:
                last_backup_age = age_from_stop_time

        assert chunk_data["job_name"] is not None
        # We use .get() for keys that were added to the agent output for backward compatibility
        client = VeeamClient(
            raw_status=chunk_data["status"],
            job_name=chunk_data["job_name"],
            total_size_byte=_parse_int(chunk_data["total_size_byte"]),
            read_size_byte=_parse_int(chunk_data.get("read_size_byte")),
            transferred_size_byte=_parse_int(chunk_data.get("transferred_size_byte")),
            start_time=_parse_datetime(chunk_data["start_time"]),
            last_backup_age=last_backup_age,
            duration=_parse_duration(chunk_data["duration"]),
            avg_speed_bps=_parse_int(chunk_data["avg_speed_bps"]),
            display_name=chunk_data["display_name"],
            backup_server=chunk_data.get("backup_server"),
        )
        data[client.job_name] = client
    return data


def discover_veeam_client(section: Section) -> DiscoveryResult:
    yield from (Service(item=job) for job in section)


def _check_backup_age(data: VeeamClient, params: CheckParameters) -> CheckResult:
    if data.last_backup_age is None:
        yield Result(state=State.CRIT, summary="No complete backup")
        return
    elif data.last_backup_age is SENTINEL_STOPTIME_RUNNING:
        # Backward compatible StopTime hack
        return

    yield from check_levels(
        data.last_backup_age,
        levels_upper=params["age"],
        render_func=render.timespan,
        label="Time since last backup",
    )


def check_veeam_client(item: str, params: CheckParameters, section: Section) -> CheckResult:
    try:
        data = section[item]
    except KeyError:
        yield Result(state=State.UNKNOWN, summary="Client not found in agent output")
        return

    infotexts = []

    state = data.status.as_state() if data.status else State.UNKNOWN
    infotexts.append(f"Status: {data.raw_status}")

    size_info = []
    size_legend = []
    metrics = []

    # Output the sizes that Veeam reported
    for key, metric_name, legend in (
        ("total_size_byte", "totalsize", "total"),
        ("read_size_byte", "readsize", "read"),
        ("transferred_size_byte", "transferredsize", "transferred"),
    ):
        size_byte: int | None
        if (size_byte := getattr(data, key, None)) is None:
            continue
        metrics.append(Metric(metric_name, size_byte))
        size_info.append(render.bytes(size_byte))
        size_legend.append(legend)

    if size_info:
        infotexts.append("Size ({}): {}".format("/".join(size_legend), "/ ".join(size_info)))

    # LastBackupAge and StopTime are only meaningful when the job is not running.
    check_age = data.status and not data.status.is_running()

    # Information may be missing
    if check_age and data.duration is not None:
        infotexts.append(f"Duration: {render.timespan(data.duration)}")
        metrics.append(Metric("duration", data.duration))

    if data.avg_speed_bps is not None:
        metrics.append(Metric("avgspeed", data.avg_speed_bps))
        infotexts.append(f"Average Speed: {render.iobandwidth(data.avg_speed_bps)}")

    # Append backup server if available
    if data.backup_server:
        infotexts.append(f"Backup server: {data.backup_server}")

    yield Result(state=state, summary=", ".join(infotexts))

    if check_age:
        yield from _check_backup_age(data, params)

    yield from metrics


agent_section_veeam_client = AgentSection(
    name="veeam_client",
    parse_function=parse_veeam_client,
)

check_plugin_veeam_client = CheckPlugin(
    name="veeam_client",
    service_name="VEEAM Client %s",
    discovery_function=discover_veeam_client,
    check_function=check_veeam_client,
    check_ruleset_name="veeam_backup",
    check_default_parameters=CheckParameters(
        age=("fixed", (108000.0, 172800.0)),  # 30h/2d
    ),
)
