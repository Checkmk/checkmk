#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import render


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
        else:
            if last_status and len(line) == 2:
                data[last_found][line[0]] = line[1]
    return data


def inventory_veeam_client(parsed):
    for job in parsed:
        yield job, {}


def check_veeam_client(item, params, parsed):  # pylint: disable=too-many-branches
    # Fallback for old None item version
    # FIXME Can be remvoed in CMK 2.0
    if item is None and len(parsed) > 0:
        item = list(parsed)[0]

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

    # Bugged agent plugins were reporting . instead of : as separator for
    # the time. This has been fixed in the agent, but be compatible to old agent.
    timesep = ":"
    if "StopTime" in data and timesep not in data["StopTime"]:
        timesep = "."

    # Check Stop time in any case, that we can catch hanging backups
    if "StopTime" not in data:
        state = 2
        infotexts.append("No complete Backup(!!)")
    # If the Backup currently is running, the stop time is strange.
    elif data["StopTime"] != "01.01.1900 00" + timesep + "00" + timesep + "00":
        stop_time = time.mktime(
            time.strptime(data["StopTime"], "%d.%m.%Y %H" + timesep + "%M" + timesep + "%S")
        )
        now = time.time()
        age = now - stop_time
        warn, crit = params["age"]
        levels = ""
        label = ""
        if age >= crit:
            state = 2
            label = "(!!)"
            levels = " (Warn/Crit: {}/{})".format(
                render.timespan(warn),
                render.timespan(crit),
            )
        elif age >= warn:
            state = max(state, 1)
            label = "(!)"
            levels = " (Warn/Crit: {}/{})".format(
                render.timespan(warn),
                render.timespan(crit),
            )
        infotexts.append(f"Last backup: {render.timespan(age)} ago{label}{levels}")

    # Check duration only if currently not running
    if data["Status"] not in ["InProgress", "Pending"]:
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
    parse_function=parse_veeam_client,
    service_name="VEEAM Client %s",
    discovery_function=inventory_veeam_client,
    check_function=check_veeam_client,
    check_ruleset_name="veeam_backup",
    check_default_parameters={
        "age": (108000, 172800),  # 30h/2d
    },
)
