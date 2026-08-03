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

Section = dict[str, dict[str, str]]


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


def _check_backup_age(
    data: dict[str, str], params: Mapping[str, Any], state: State
) -> tuple[State, str | None]:
    if (backup_age := data.get("LastBackupAge")) is not None:
        age = float(backup_age)
    # elif section (StopTime) kept for compatibility with old agent version
    # that was reporting StopTime and not LastBackupAge
    elif (stop_time := data.get("StopTime")) is not None:
        # If the Backup is currently running, the stop time is strange
        if stop_time == "01.01.1900 00:00:00":
            return state, None

        stop_time_epoch = time.mktime(time.strptime(stop_time, "%d.%m.%Y %H:%M:%S"))
        age = time.time() - stop_time_epoch
    else:
        return State.CRIT, "No complete Backup(!!)"

    warn, crit = params["age"]
    levels = ""
    label = ""
    if age >= crit:
        state = State.CRIT
        label = "(!!)"
        levels = f" (Warn/Crit: {render.timespan(warn)}/{render.timespan(crit)})"
    elif age >= warn:
        state = State.worst(state, State.WARN)
        label = "(!)"
        levels = f" (Warn/Crit: {render.timespan(warn)}/{render.timespan(crit)})"

    return state, f"Last backup: {render.timespan(age)} ago{label}{levels}"


def check_veeam_client(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
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
    if data["Status"] == "Failed":
        state = State.CRIT
    infotexts.append(f"Status: {data['Status']}")

    # Only output the Job name
    if data.get("JobName"):
        infotexts.append(f"Job: {data['JobName']}")

    size_info = []
    size_legend = []
    metrics = []

    total_size_byte = int(data["TotalSizeByte"])
    metrics.append(Metric("totalsize", total_size_byte))
    size_info.append(render.bytes(total_size_byte))
    size_legend.append("total")

    # Output ReadSize and TransferedSize if available
    if "ReadSizeByte" in data:
        read_size_byte = int(data["ReadSizeByte"])
        metrics.append(Metric("readsize", read_size_byte))
        size_info.append(render.bytes(read_size_byte))
        size_legend.append("read")

    if "TransferedSizeByte" in data:
        transfered_size_byte = int(data["TransferedSizeByte"])
        metrics.append(Metric("transferredsize", transfered_size_byte))
        size_info.append(render.bytes(transfered_size_byte))
        size_legend.append("transferred")

    infotexts.append("Size ({}): {}".format("/".join(size_legend), "/ ".join(size_info)))

    # Check duration only if currently not running
    if data["Status"] not in ["InProgress", "Pending"]:
        # when status is "InProgress" or "Pending"
        # lastBackupAge and StopTime have strange values
        state, info = _check_backup_age(data, params, state)
        if info is not None:
            infotexts.append(info)

        # Information may missing
        if data.get("DurationDDHHMMSS"):
            duration = 0
            days, hours, minutes, seconds = map(int, data["DurationDDHHMMSS"].split(":"))
            duration += seconds
            duration += minutes * 60
            duration += hours * 60 * 60
            duration += days * 60 * 60 * 24
            infotexts.append(f"Duration: {render.timespan(duration)}")
            metrics.append(Metric("duration", duration))

    if "AvgSpeedBps" in data:
        avg_speed_bps = int(data["AvgSpeedBps"])
        metrics.append(Metric("avgspeed", avg_speed_bps))
        infotexts.append(f"Average Speed: {render.iobandwidth(avg_speed_bps)}")

    # Append backup server if available
    if "BackupServer" in data:
        infotexts.append(f"Backup server: {data['BackupServer']}")

    yield Result(state=state, summary=", ".join(infotexts))
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
    check_default_parameters={
        "age": (108000, 172800),  # 30h/2d
    },
)
