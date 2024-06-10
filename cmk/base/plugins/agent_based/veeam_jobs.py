#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<veeam_jobs:sep(9) >>>
# BACKUP_RIS      Backup  Stopped Success 27.10.2013 22:00:17     27.10.2013 22:06:12
# BACKUP_R43-local_HXWH44 Backup  Stopped Success 26.10.2013 18:00:20     26.10.2013 18:46:03
# BACKUP_R43-Pool4_HXWH44 Backup  Stopped Failed  26.10.2013 23:13:13     27.10.2013 00:51:17
# BACKUP_R43-Pool3_HXWH44 Backup  Stopped Failed  27.10.2013 02:59:29     27.10.2013 08:59:51
# REPL_KNESXIDMZ  Replica Stopped Success 27.10.2013 44:00:01     27.10.2013 44:44:26
# BACKUP_KNESXI   Backup  Stopped Success 28.10.2013 05:00:04     28.10.2013 05:32:15
# BACKUP_KNESXit  Backup  Stopped Success 26.10.2013 22:30:02     27.10.2013 02:37:30
# BACKUP_R43-Pool5_HXWH44 Backup  Stopped Success 27.10.2013 23:00:00     27.10.2013 23:04:53
# BACKUP_R43-Pool2_HXWH44 Backup  Stopped Failed  27.10.2013 02:37:45     27.10.2013 02:45:35


from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


def discovery_veeam_jobs(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_veeam_jobs(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if len(line) < 6:
            continue  # Skip incomplete lines

        job_name, job_type, job_last_state, job_last_result, job_creation_time, job_end_time = line[
            :6
        ]

        if job_name != item:
            continue  # Skip not matching lines

        if job_last_state in ["Starting", "Working", "Postprocessing"]:
            summary = f"Running since {job_creation_time} (current state is: {job_last_state})"
            yield Result(state=State.OK, summary=summary)
            return

        if job_last_result == "Success":
            state = State.OK
        elif job_last_state == "Idle" and job_type == "BackupSync":
            # A sync job is always idle
            state = State.OK
        elif job_last_result == "Failed":
            state = State.CRIT
        elif job_last_state == "Stopped" and job_last_result == "Warning":
            state = State.WARN
        else:
            state = State.UNKNOWN

        yield Result(state=State.OK, summary=f"State: {job_last_state}")
        yield Result(state=state, summary=f"Result: {job_last_result}")
        yield Result(state=State.OK, summary=f"Creation time: {job_creation_time}")
        yield Result(state=State.OK, summary=f"End time: {job_end_time}")
        yield Result(state=State.OK, summary=f"Type: {job_type}")


def parse_veeam_jobs(string_table: StringTable) -> StringTable:
    return string_table


register.agent_section(
    name="veeam_jobs",
    parse_function=parse_veeam_jobs,
)

register.check_plugin(
    name="veeam_jobs",
    service_name="VEEAM Job %s",
    discovery_function=discovery_veeam_jobs,
    check_function=check_veeam_jobs,
)
