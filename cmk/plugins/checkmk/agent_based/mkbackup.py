#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<mkbackup>>>
# [[[site:heute2:encrypted]]]
# {'bytes_per_second': 0,
#  'finished': 1467733556.67532,
#  'output': '2016-07-05 17:45:56 --- Starting backup (Check_MK-Klappspaten-heute2-encrypted) ---\n2016-07-05 17:45:56 Cleaning up previously completed backup\n2016-07-05 17:45:56
# --- Backup completed (Duration: 0:00:00, Size: 6.49 MB, IO: 0.00 B/s) ---\n',
#  'pid': 14850,
#  'size': 6809879,
#  'started': 1467733556.39216,
#  'state': 'finished',
#  'success': True}
#
# <<<mkbackup>>>
# [[[system:backup-single]]]
# {
#     "bytes_per_second": 141691.8939750615,
#     "finished": 1468914936.47381,
#     "next_schedule": 1468973400.0,
#     "output": "2016-07-19 07:55:07 --- Starting backup (Check_MK_Appliance-alleine-backup+single to klappspaten) ---\n2016-07-19 07:55:07 Performing system backup (system.tar)\n2016-07-19 07:55:10 Performing system data backup (system-data.tar)\n2016-07-19 07:55:19 Performing site backup: migrate\n2016-07-19 07:55:19 The Check_MK version of this site does not support online backups. The site seems to be at least partially running. Stopping the site during backup and starting it again after completion.\n2016-07-19 07:55:19 Stopping site\n2016-07-19 07:55:23 Start offline site backup\n2016-07-19 07:55:23 Starting site again\n2016-07-19 07:55:27 Performing site backup: test\n2016-07-19 07:55:35 Verifying backup consistency\n2016-07-19 07:55:36 Cleaning up previously completed backup\n2016-07-19 07:55:36 --- Backup completed (Duration: 0:00:28, Size: 380.65 MB, IO: 138.37 kB/s) ---\n",
#     "pid": 28038,
#     "size": 399144997,
#     "started": 1468914907.521488,
#     "state": "finished",
#     "success": true
# }


import json
import time
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

JobData = dict[str, Any]
BackupData = dict[str, dict[str, JobData]]


def parse_mkbackup(string_table: StringTable) -> BackupData:
    parsed: BackupData = {}

    job, json_data = None, ""
    for l in string_table:
        line = " ".join(l)
        if line.startswith("[[["):
            head = line[3:-3].split(":")
            if len(head) == 3:
                site_id, job_id = head[1:]
                sites = parsed.setdefault("site", {})
                jobs = sites.setdefault(site_id, {})
                job = jobs[job_id] = {}
            else:
                job_id = head[-1]
                system = parsed.setdefault("system", {})
                job = system[job_id] = {}

        elif job is not None:
            json_data += line
            if line == "}":
                job.update(json.loads(json_data))
                json_data = ""

    return parsed


def check_mkbackup(job_state: JobData) -> CheckResult:
    if job_state["state"] in ["started", "running"]:
        duration = time.time() - job_state["started"]

        yield Result(
            state=State.OK,
            summary="The job is running for %s since %s"
            % (
                render.timespan(duration),
                render.datetime(job_state["started"]),
            ),
        )
        yield Metric(name="backup_duration", value=duration)
        yield Metric(name="backup_avgspeed", value=job_state["bytes_per_second"])

    elif job_state["state"] == "finished":
        if job_state["success"] is False:
            yield Result(state=State.CRIT, summary="Backup failed")
        else:
            yield Result(state=State.OK, summary="Backup completed")

        duration = job_state["finished"] - job_state["started"]
        yield Result(
            state=State.OK,
            summary="it was running for %s from %s till %s"
            % (
                render.timespan(duration),
                render.datetime(job_state["started"]),
                render.datetime(job_state["finished"]),
            ),
        )
        yield Metric(name="backup_duration", value=duration)
        yield Metric(name="backup_avgspeed", value=job_state["bytes_per_second"])

        if "size" in job_state and job_state.get("success", False):
            yield Result(
                state=State.OK,
                summary="Size: %s" % render.bytes(job_state["size"]),
            )
            yield Metric(name="backup_size", value=job_state["size"])

        next_run = job_state["next_schedule"]
        if next_run == "disabled":
            yield Result(state=State.WARN, summary="Schedule is currently disabled")

        elif next_run is not None:
            # add a 30 seconds buffer to prevent a critical when the backup is about to start
            if next_run < time.time() + 30:
                state = State.CRIT
            else:
                state = State.OK
            yield Result(state=state, summary="Next run: %s" % render.datetime(next_run))


def discover_mkbackup_system(section: Any) -> DiscoveryResult:
    for job_id in section.get("system", {}):
        yield Service(item=job_id)


def check_mkbackup_system(item: str, section: BackupData) -> CheckResult:
    job_state = section.get("system", {}).get(item)
    if not job_state:
        return None

    yield from check_mkbackup(job_state)


agent_section_mkbackup = AgentSection(name="mkbackup", parse_function=parse_mkbackup)
check_plugin_mkbackup = CheckPlugin(
    name="mkbackup",
    service_name="Backup %s",
    discovery_function=discover_mkbackup_system,
    check_function=check_mkbackup_system,
)


def discover_mkbackup_site(section: Any) -> DiscoveryResult:
    for site_id, jobs in section.get("site", {}).items():
        for job_id in jobs:
            yield Service(item=f"{site_id} backup {job_id}")


def check_mkbackup_site(item: str, section: BackupData) -> CheckResult:
    site_id, job_id = item.split(" backup ")
    job_state = section.get("site", {}).get(site_id, {}).get(job_id)
    if not job_state:
        return None

    yield from check_mkbackup(job_state)


check_plugin_mkbackup_site = CheckPlugin(
    name="mkbackup_site",
    service_name="OMD %s",
    sections=["mkbackup"],
    discovery_function=discover_mkbackup_site,
    check_function=check_mkbackup_site,
)
