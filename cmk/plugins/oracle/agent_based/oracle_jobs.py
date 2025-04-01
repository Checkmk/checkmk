#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_jobs>>>
# IODBSZ1 SYS SM$CLEAN_AUTO_SPLIT_MERGE SCHEDULED 0 763 TRUE 24.04.13 00:00:00,600000 EUROPE/VIENNA - SUCCEEDED
# IODBSZ1 SYS RSE$CLEAN_RECOVERABLE_SCRIPT SCHEDULED 0 763 TRUE 24.04.13 00:00:00,100000 EUROPE/VIENNA - SUCCEEDED
# IODBSZ1 SYS BSLN_MAINTAIN_STATS_JOB SCHEDULED 0 110 TRUE 29.04.13 00:00:00,300000 +01:00 BSLN_MAINTAIN_STATS_SCHED SUCCEEDED
# IODBSZ1 SYS DRA_REEVALUATE_OPEN_FAILURES SCHEDULED 0 97 TRUE 01.01.70 00:00:00,000000 +02:00 MAINTENANCE_WINDOW_GROUP SUCCEEDED
# IODBSZ1 SYS ORA$AUTOTASK_CLEAN SCHEDULED 0 763 TRUE 24.04.13 03:00:00,900000 EUROPE/VIENNA DAILY_PURGE_SCHEDULE SUCCEEDED
# IODBSZ1 SYS PURGE_LOG SCHEDULED 0 763 TRUE 24.04.13 03:00:00,800000 EUROPE/VIENNA DAILY_PURGE_SCHEDULE SUCCEEDED
# IODBSZ1 ORACLE_OCM MGMT_CONFIG_JOB SCHEDULED 0 97 TRUE 01.01.70 00:00:00,000000 +02:00 MAINTENANCE_WINDOW_GROUP SUCCEEDED
# IODBSZ1 ORACLE_OCM MGMT_STATS_CONFIG_JOB SCHEDULED 0 3 TRUE 01.05.13 01:01:01,000000 +01:00 - SUCCEEDED
# IODBSZ1 EXFSYS RLM$SCHDNEGACTION SCHEDULED 0 18954 TRUE 23.04.13 14:51:57,000000 +02:00 - SUCCEEDED
# IODBSZ1 EXFSYS RLM$EVTCLEANUP SCHEDULED 0 18202 TRUE 23.04.13 13:41:48,200000 +01:00 - SUCCEEDED

# new output
# <<<oracle_jobs:sep(124)>>>
# QS1|SYS|SM$CLEAN_AUTO_SPLIT_MERGE|SCHEDULED|1|877|TRUE|02-AUG-15 12.00.00.500000 AM EUROPE/VIENNA|-|SUCCEEDED
# QS1|SYS|RSE$CLEAN_RECOVERABLE_SCRIPT|SCHEDULED|0|877|TRUE|02-AUG-15 12.00.00.800000 AM EUROPE/VIENNA|-|SUCCEEDED
# QS1|SYS|FGR$AUTOPURGE_JOB|DISABLED||0|FALSE|01-JAN-70 12.00.00.000000 AM +02:00|-|
# QS1|SYS|BSLN_MAINTAIN_STATS_JOB|SCHEDULED|12|128|TRUE|02-AUG-15 12.00.00.600000 AM +01:00|BSLN_MAINTAIN_STATS_SCHED|SUCCEEDED
# QS1|SYS|DRA_REEVALUATE_OPEN_FAILURES|SCHEDULED|0|156|TRUE|01-JAN-70 12.00.00.000000 AM +02:00|MAINTENANCE_WINDOW_GROUP|SUCCEEDED
# QS1|SYS|HM_CREATE_OFFLINE_DICTIONARY|DISABLED||0|FALSE|01-JAN-70 12.00.00.000000 AM +02:00|MAINTENANCE_WINDOW_GROUP|
# QS1|SYS|ORA$AUTOTASK_CLEAN|SCHEDULED|0|877|TRUE|02-AUG-15 03.00.00.200000 AM EUROPE/VIENNA|DAILY_PURGE_SCHEDULE|SUCCEEDED
# QS1|SYS|FILE_WATCHER|DISABLED||0|FALSE|01-JAN-70 12.00.00.000000 AM +02:00|FILE_WATCHER_SCHEDULE|
# QS1|SYS|PURGE_LOG|SCHEDULED|0|877|TRUE|02-AUG-15 03.00.00.700000 AM EUROPE/VIENNA|DAILY_PURGE_SCHEDULE|SUCCEEDED
# QS1|ORACLE_OCM|MGMT_STATS_CONFIG_JOB|DISABLED|0|2|FALSE|01-MAY-15 01.01.01.100000 AM +01:00|-|
# QS1|ORACLE_OCM|MGMT_CONFIG_JOB|DISABLED|0|40|FALSE|08-APR-15 01.01.01.200000 AM +01:00|-|
# QS1|DBADMIN|DATENEXPORT-FUR|COMPLETED|0|3|FALSE|22-AUG-14 01.11.00.000000 AM EUROPE/BERLIN|-|


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_oracle_jobs(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) <= 2:
            continue
        # old format < RDBMS 12.1
        if 3 <= len(line) <= 10:
            yield Service(item=f"{line[0]}.{line[1]}.{line[2]}")
        else:
            # new format: sid.pdb_name.job_owner.job_name
            yield Service(item=f"{line[0]}.{line[1]}.{line[2]}.{line[3]}")


def check_oracle_jobs(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    # only extract the sid from item.
    sid = item[0 : item.index(".", 0)]

    data_found = False

    for line in section:
        service_found = False

        if len(line) < 2:
            # ignore wrong/corrupted lines
            continue

        if line[1].startswith(" Debug "):
            # Skip invalid lines from Agent
            continue

        # we need to check against valid lines before the following comparisonq
        if line[0] == sid:
            data_found = True

        # check for pdb_name in agent output
        # => the agentoutput is responsible for the format of item from Checkmk!
        # item could have the following formats. Keep in mind, that job_name could include a '.'!
        if len(line) == 11 and item.count(".") >= 3:
            # => sid.pdb_name.job_owner.job_name
            itemsid, itempdb, itemowner, itemname = item.split(".", 3)
            lineformat = 3

            (
                sid,
                job_pdb,
                job_owner,
                job_name,
                job_state,
                job_runtime,
                _job_run_count,
                job_enabled,
                job_nextrun,
                job_schedule,
                job_last_state,
            ) = line

        elif len(line) == 10:
            # sid.job_owner.job_name
            itemsid, itemowner, itemname = item.split(".", 2)
            itempdb = ""
            lineformat = 2

            (
                sid,
                job_owner,
                job_name,
                job_state,
                job_runtime,
                _job_run_count,
                job_enabled,
                job_nextrun,
                job_schedule,
                job_last_state,
            ) = line

        elif len(line) > 8:
            # really old plugins without job_owner...
            # The > 8 is expected, due to missing field seperator.
            # this should be removed in a future release!

            # sid.job_name
            itemsid, itemname = item.split(".", 1)
            itempdb = ""
            itemowner = ""
            lineformat = 1

            job_name = line[2]
            job_state = line[3]
            job_runtime = line[4]
            job_enabled = line[6]
            job_nextrun = " ".join(line[7:-3])
            job_schedule = line[-2]
            job_last_state = line[-1]

        else:
            # invalid line/format from agent
            continue

        if (
            (
                lineformat == 3
                and itemname == job_name
                and itemowner == job_owner
                and itempdb == job_pdb
                and itemsid == sid
            )
            or (
                lineformat == 2
                and itemname == job_name
                and itemowner == job_owner
                and itemsid == sid
            )
            or (lineformat == 1 and itemname == job_name and itemsid == sid)
        ):
            service_found = True
            param_consider_job_status = params["consider_job_status"]

            break

    if not data_found:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login not possible for check %s" % item)

    if not service_found:
        # 'missingjob' was once used in the default parameters, so we still need to keep this key
        # for old autochecks file to continue working.
        yield Result(
            state=State(params.get("status_missing_jobs", params.get("missingjob", 2))),
            summary="Job is missing",
        )
        return

    state = State.OK
    output = []
    perfdata = []

    txt = "Job-State: %s" % job_state
    if job_state == "BROKEN":
        txt += "(!!)"
        state = State.CRIT
    output.append(txt)

    txt = "Enabled: %s" % (job_enabled == "TRUE" and "Yes" or "No")
    if job_enabled != "TRUE" and job_state != "RUNNING":
        if param_consider_job_status == "ignore":
            txt += " (ignored)"
        else:
            txt += "(!)"
            state = State.worst(state, State.WARN)
    output.append(txt)

    if job_runtime in {"", "SCHEDULED"}:
        last_duration = 0
    else:
        last_duration = int(job_runtime.replace(".", ",").split(",", 1)[0])
        # bugfix for an error in mk_oracle agent with missing round over last_duration
        output.append("Last Duration: %s" % (render.timespan(last_duration)))

    if "run_duration" in params:
        warn, crit = params["run_duration"]

        output.append(" (warn/crit at %ds/%ds)" % (warn, crit))

        if last_duration >= crit:
            output.append("(!!)")
            state = State.worst(state, State.CRIT)
        elif last_duration >= warn:
            output.append("(!)")
            state = State.worst(state, State.WARN)

    perfdata.append(Metric("duration", last_duration))

    # 01.05.13 01:01:01,000000 +01:00
    if job_nextrun.startswith("01.01.70 00:00:00"):
        if job_schedule == "-" and job_state != "DISABLED":
            job_nextrun = "not scheduled(!)"
            state = State.worst(state, State.WARN)
        else:
            job_nextrun = job_schedule
    output.append("Next Run: %s" % job_nextrun)

    if "missinglog" in params:
        missinglog = params["missinglog"]
    else:
        missinglog = 1

    # A job who is running forever has no last run state and job_last_state is
    # STOPPED
    if job_state == "RUNNING" and job_runtime == "" and job_last_state == "STOPPED":
        txt = "Job is running forever"
    elif job_last_state == "":
        # no information from job log (outer join in SQL is empty)
        txt = " no log information found"

        if missinglog == 0:
            txt += " (ignored)"
        elif missinglog == 1:
            txt += "(!)"
        elif missinglog == 2:
            txt += "(!!)"
        elif missinglog == 3:
            txt += "(?)"
        output.append(txt)

        state = State.worst(state, State(missinglog))

    else:
        txt = "Last Run Status: %s" % (job_last_state)

        if job_enabled == "TRUE" and job_last_state != "SUCCEEDED":
            state = State.worst(state, State.CRIT)
        else:
            txt += " (ignored disabled Job)"
        output.append(txt)

    if job_state == "DISABLED" and "status_disabled_jobs" in params:
        state = State(params["status_disabled_jobs"])

    yield Result(state=state, summary=", ".join(output))
    yield from perfdata


def parse_oracle_jobs(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_jobs = AgentSection(
    name="oracle_jobs",
    parse_function=parse_oracle_jobs,
)

check_plugin_oracle_jobs = CheckPlugin(
    name="oracle_jobs",
    service_name="ORA %s Job",
    discovery_function=inventory_oracle_jobs,
    check_function=check_oracle_jobs,
    check_ruleset_name="oracle_jobs",
    check_default_parameters={
        "consider_job_status": "ignore",
        "missinglog": 1,
        "status_missing_jobs": 2,
    },
)
