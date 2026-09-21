#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
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

Section = dict[str, dict[str, str]]


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


def parse_veeam_client(string_table: StringTable) -> Section:
    data: Section = {}
    last_status: str | bool = False
    last_found: str = ""
    for line in string_table:
        if line[0] == "Status":
            # Prevent empty entries
            last_status = line[1] if len(line) == 2 else False
        elif line[0] == "JobName":
            if last_status:
                last_found = line[1]
                data[last_found] = {}
                data[last_found]["Status"] = str(last_status)
        elif last_status and len(line) == 2:
            data[last_found][line[0]] = line[1]
    return data


def discover_veeam_client(section: Section) -> DiscoveryResult:
    yield from (Service(item=job) for job in section)


def _check_backup_age(data: dict[str, str], params: CheckParameters) -> CheckResult:
    age = _parse_float(data.get("LastBackupAge"))
    if age is None:
        # StopTime is kept for compatibility with old agent versions that reported
        # StopTime instead of LastBackupAge.
        if (stop_time := data.get("StopTime")) is None:
            yield Result(state=State.CRIT, summary="No complete backup")
            return

        # While a backup is running the stop time is not meaningful.
        if stop_time == "01.01.1900 00:00:00":
            return

        try:
            stop_time_epoch = time.mktime(time.strptime(stop_time, "%d.%m.%Y %H:%M:%S"))
        except ValueError:
            yield Result(state=State.CRIT, summary="No complete backup")
            return
        age = time.time() - stop_time_epoch

    yield from check_levels(
        age,
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

    state = State.OK
    # Append current Status to Output
    if data["Status"] == "Warning":
        state = State.WARN
    elif data["Status"] == "Failed":
        state = State.CRIT
    infotexts.append(f"Status: {data['Status']}")

    # Only output the Job name
    if data.get("JobName"):
        infotexts.append(f"Job: {data['JobName']}")

    size_info = []
    size_legend = []
    metrics = []

    # Output the sizes that Veeam reported
    for key, metric_name, legend in (
        ("TotalSizeByte", "totalsize", "total"),
        ("ReadSizeByte", "readsize", "read"),
        ("TransferedSizeByte", "transferredsize", "transferred"),
    ):
        if (size_byte := _parse_int(data.get(key))) is None:
            continue
        metrics.append(Metric(metric_name, size_byte))
        size_info.append(render.bytes(size_byte))
        size_legend.append(legend)

    if size_info:
        infotexts.append("Size ({}): {}".format("/".join(size_legend), "/ ".join(size_info)))

    # LastBackupAge and StopTime are only meaningful when the job is not running.
    check_age = data["Status"] not in ["InProgress", "Pending"]

    # Information may be missing
    if check_age and (duration := _parse_duration(data.get("DurationDDHHMMSS"))) is not None:
        infotexts.append(f"Duration: {render.timespan(duration)}")
        metrics.append(Metric("duration", duration))

    if (avg_speed_bps := _parse_int(data.get("AvgSpeedBps"))) is not None:
        metrics.append(Metric("avgspeed", avg_speed_bps))
        infotexts.append(f"Average Speed: {render.iobandwidth(avg_speed_bps)}")

    # Append backup server if available
    if "BackupServer" in data:
        infotexts.append(f"Backup server: {data['BackupServer']}")

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
