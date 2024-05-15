#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<aix_sap_processlist:sep(44)>>>
# [01]
# 23.03.2015 13:49:27
# GetProcessList
# OK
# name, description, dispstatus, textstatus, starttime, elapsedtime, pid
# msg_server, MessageServer, GREEN, Running, 2015 03 23 05:03:45, 8:45:42, 17563666
# disp+work, Dispatcher, GREEN, Running, Message Server connection ok, Dialog Queue time: 0.00 sec, 2015 03 23 05:03:45, 8:45:42, 15335532
# igswd_mt, IGS Watchdog, GREEN, Running, 2015 03 23 05:03:45, 8:45:42, 31326312
#
# <<<aix_sap_processlist:sep(44)>>>
# [02]
# 23.03.2015 13:59:27
# GetProcessList
# FAIL: NIECONN_REFUSED (Connection refused), NiRawConnect failed in plugin_fopen()

# <<<aix_sap_processlist:sep(44)>>>
# [04]
# 10.01.2017 09:10:41
# GetProcessList
# OK
# name, description, dispstatus, textstatus, starttime, elapsedtime, pid
# msg_server, MessageServer, GREEN, Running, 2017 01 08 14:38:18, 42:32:23, 12714224
# disp+work, Dispatcher, GREEN, Running, 2017 01 08 14:38:18, 42:32:23, 15794214
# aaaaaaaa, Central Syslog Collector, GRAY, Stopped, , , 9961478
# bbbbbbbb, Central Syslog Sender, GRAY, Stopped, , , 9109548


# mypy: disable-error-code="var-annotated"

import re
import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import render


def parse_aix_sap_processlist(string_table):
    instance, description = None, None
    parsed = {}
    for line in string_table:
        if line[0].startswith("["):
            instance = line[0][1:-1]

        elif instance and line[0].startswith("FAIL:"):
            instance = None

        elif instance and len(line) == 7 and line[-1] != " pid":
            description, status, textstatus, start = (re.sub("^ ", "", x) for x in line[1:5])

        elif instance and len(line) == 9:
            description, status, textstatus = (re.sub("^ ", "", x) for x in line[1:4])
            start = re.sub("^ ", "", line[6])

        else:
            continue

        if instance is not None and description is not None:
            itemname = f"{description} on Instance {instance}"
            parsed.setdefault(itemname, {"status": status, "textstatus": textstatus})
            try:
                parsed[itemname]["start_time"] = time.strptime(start, "%Y %m %d %H:%M:%S")
            except ValueError:
                continue

    return parsed


def inventory_aix_sap_processlist(parsed):
    for entry in parsed:
        yield entry, None


def check_aix_sap_processlist(item, _no_params, parsed):
    if item in parsed:
        data = parsed[item]
        status = data["status"]
        textstatus = data["textstatus"]
        infotexts = ["Status: %s" % textstatus]
        perfdata = []

        if "start_time" in data:
            start_time = data["start_time"]
            start = time.strftime("%c", start_time)
            elapsed = time.time() - time.mktime(start_time)
            perfdata = [("runtime", elapsed)]
            infotexts.append(f"Start Time: {start}, Elapsed Time: {render.timespan(elapsed)}")

        if status == "GREEN":
            state = 0
        elif status == "YELLOW":
            state = 1
        else:
            state = 2
        return state, ", ".join(infotexts), perfdata
    return None


check_info["aix_sap_processlist"] = LegacyCheckDefinition(
    parse_function=parse_aix_sap_processlist,
    service_name="SAP Process %s",
    discovery_function=inventory_aix_sap_processlist,
    check_function=check_aix_sap_processlist,
)
