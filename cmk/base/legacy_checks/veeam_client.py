#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_veeam_client(string_table):
    data = {}
    for line in string_table:
        if line[0] == "Status":
            if len(line) == 2:
                last_status = line[1]
            else:
                # Prevent empty entries
                last_status = False
        elif line[0] == "JobName":
            if last_status:
                last_found = line[1]
                data[last_found] = {}
                data[last_found]["Status"] = last_status
        elif last_status and len(line) == 2:
            data[last_found][line[0]] = line[1]
    return data


def discover_veeam_client(parsed):
    for job in parsed:
        yield job, {}


def _check_backup_age(data, params, state):
    if (backup_age := data.get("LastBackupAge")) is not None:
        age = float(backup_age)
    # elif section (StopTime) kept for compatibility with old agent version
    # that was reporting StopTime and not LastBackupAge
    elif (stop_time := data.get("StopTime")) is not None:
        # If the Backup is currently running, the stop time is strange
        if stop_time == "01.01.1900 00:00:00":
            return state, None

        stop_time = time.mktime(time.strptime(stop_time, "%d.%m.%Y %H:%M:%S"))
        age = time.time() - stop_time
    else:
        return 2, "No complete Backup(!!)"

    warn, crit = params["age"]
    levels = ""
    label = ""
    if age >= crit:
        state = 2
        label = "(!!)"
        levels = f" (Warn/Crit: {render.timespan(warn)}/{render.timespan(crit)})"
    elif age >= warn:
        state = max(state, 1)
        label = "(!)"
        levels = f" (Warn/Crit: {render.timespan(warn)}/{render.timespan(crit)})"

    return state, f"Last backup: {render.timespan(age)} ago{label}{levels}"


def check_veeam_client(item, params, parsed):
    try:
        data = parsed[item]
    except KeyError:
        return 3, "Client not found in agent output"

    perfdata = []
    infotexts = []

    state = 0
    # Append current Status to Output
    if data["Status"] == "Warning":
        state = 1
    if data["Status"] == "Failed":
        state = 2
    infotexts.append("Status: %s" % data["Status"])

    # Only output the Job name
    if data.get("JobName"):
        infotexts.append("Job: %s" % data["JobName"])

    size_info = []
    size_legend = []

    TotalSizeByte = int(data["TotalSizeByte"])
    perfdata.append(("totalsize", TotalSizeByte))
    size_info.append(render.bytes(TotalSizeByte))
    size_legend.append("total")

    # Output ReadSize and TransferedSize if available
    if "ReadSizeByte" in data:
        ReadSizeByte = int(data["ReadSizeByte"])
        perfdata.append(("readsize", ReadSizeByte))
        size_info.append(render.bytes(ReadSizeByte))
        size_legend.append("read")

    if "TransferedSizeByte" in data:
        TransferedSizeByte = int(data["TransferedSizeByte"])
        perfdata.append(("transferredsize", TransferedSizeByte))
        size_info.append(render.bytes(TransferedSizeByte))
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
            infotexts.append("Duration: %s" % render.timespan(duration))
            perfdata.append(("duration", duration))

    if "AvgSpeedBps" in data:
        avg_speed_bps = int(data["AvgSpeedBps"])
        perfdata.append(("avgspeed", avg_speed_bps))
        infotexts.append("Average Speed: %s" % render.iobandwidth(avg_speed_bps))

    # Append backup server if available
    if "BackupServer" in data:
        infotexts.append("Backup server: %s" % data["BackupServer"])

    return state, ", ".join(infotexts), perfdata


check_info["veeam_client"] = LegacyCheckDefinition(
    name="veeam_client",
    parse_function=parse_veeam_client,
    service_name="VEEAM Client %s",
    discovery_function=discover_veeam_client,
    check_function=check_veeam_client,
    check_ruleset_name="veeam_backup",
    check_default_parameters={
        "age": (108000, 172800),  # 30h/2d
    },
)
