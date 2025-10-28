#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

# Example Output:
# <<<msexch_dag:sep(58)>>>
# RunspaceId                       : d58353f4-f868-43b2-8404-25875841a47b
# Identity                         : Mailbox Database 1\S0141KL
# Name                             : Mailbox Database 1\S0141KL
# DatabaseName                     : Mailbox Database 1
# Status                           : Mounted
# MailboxServer                    : S0141KL
# ActiveDatabaseCopy               : s0141kl
# ActivationSuspended              : False
# ActionInitiator                  : Unknown
# ErrorMessage                     :
# ErrorEventId                     :
# ExtendedErrorInfo                :
# SuspendComment                   :
# SinglePageRestore                : 0
# ContentIndexState                : Healthy
# ContentIndexErrorMessage         :
# CopyQueueLength                  : 0
# ReplayQueueLength                : 0
# LatestAvailableLogTime           :
# LastCopyNotificationedLogTime    :
# LastCopiedLogTime                :
# LastInspectedLogTime             :
# LastReplayedLogTime              :
# LastLogGenerated                 : 0
# LastLogCopyNotified              : 0
# LastLogCopied                    : 0
# LastLogInspected                 : 0
# LastLogReplayed                  : 0
# LogsReplayedSinceInstanceStart   : 0
# LogsCopiedSinceInstanceStart     : 0
# LatestFullBackupTime             : 22.10.2014 21:55:12
# LatestIncrementalBackupTime      :
# LatestDifferentialBackupTime     :
# LatestCopyBackupTime             :
# SnapshotBackup                   : True
# SnapshotLatestFullBackup         : True
# SnapshotLatestIncrementalBackup  :
# SnapshotLatestDifferentialBackup :
# SnapshotLatestCopyBackup         :
# LogReplayQueueIncreasing         : False
# LogCopyQueueIncreasing           : False
# OutstandingDumpsterRequests      : {}
# OutgoingConnections              :
# IncomingLogCopyingNetwork        :
# SeedingNetwork                   :
# ActiveCopy                       : True
#
# RunspaceId                       : d58353f4-f868-43b2-8404-25875841a47b
# Identity                         : Mailbox Database 2\S0141KL
# Name                             : Mailbox Database 2\S0141KL
# DatabaseName                     : Mailbox Database 2
# Status                           : Healthy
# MailboxServer                    : S0141KL
# ActiveDatabaseCopy               : s0142kl
# ActivationSuspended              : False
# ActionInitiator                  : Unknown
# ErrorMessage                     :
# ErrorEventId                     :
# ExtendedErrorInfo                :
# SuspendComment                   :
# SinglePageRestore                : 0
# ContentIndexState                : Healthy
# ContentIndexErrorMessage         :
# CopyQueueLength                  : 0
# ReplayQueueLength                : 0
# LatestAvailableLogTime           : 15.12.2014 13:26:34
# LastCopyNotificationedLogTime    : 15.12.2014 13:26:34
# LastCopiedLogTime                : 15.12.2014 13:26:34
# LastInspectedLogTime             : 15.12.2014 13:26:34
# LastReplayedLogTime              : 15.12.2014 13:26:34
# LastLogGenerated                 : 2527253
# LastLogCopyNotified              : 2527253
# LastLogCopied                    : 2527253
# LastLogInspected                 : 2527253
# LastLogReplayed                  : 2527253
# LogsReplayedSinceInstanceStart   : 15949
# LogsCopiedSinceInstanceStart     : 15945
# LatestFullBackupTime             : 13.12.2014 19:06:54
# LatestIncrementalBackupTime      :
# LatestDifferentialBackupTime     :
# LatestCopyBackupTime             :
# SnapshotBackup                   : True
# SnapshotLatestFullBackup         : True
# SnapshotLatestIncrementalBackup  :
# SnapshotLatestDifferentialBackup :
# SnapshotLatestCopyBackup         :
# LogReplayQueueIncreasing         : False
# LogCopyQueueIncreasing           : False
# OutstandingDumpsterRequests      : {}
# OutgoingConnections              :
# IncomingLogCopyingNetwork        :
# SeedingNetwork                   :
# ActiveCopy                       : False


def parse_msexch_dag(string_table: StringTable) -> StringTable:
    return string_table


agent_section_msexch_dag = AgentSection(
    name="msexch_dag",
    parse_function=parse_msexch_dag,
)

#   .--dbcopy--------------------------------------------------------------.
#   |                      _ _                                             |
#   |                   __| | |__   ___ ___  _ __  _   _                   |
#   |                  / _` | '_ \ / __/ _ \| '_ \| | | |                  |
#   |                 | (_| | |_) | (_| (_) | |_) | |_| |                  |
#   |                  \__,_|_.__/ \___\___/| .__/ \__, |                  |
#   |                                       |_|    |___/                   |
#   +----------------------------------------------------------------------+


def discover_msexch_dag_dbcopy(section: StringTable) -> DiscoveryResult:
    getit = False
    key = "Status"
    dbname = None
    for line in section:
        if len(line) == 2:
            if line[0].strip() == "DatabaseName":
                dbname = line[1].strip()
                getit = True
            elif getit and line[0].strip() == key:
                yield Service(item=dbname, parameters={"inv_key": key, "inv_val": line[1].strip()})
                getit = False


def check_msexch_dag_dbcopy(
    item: str, params: Mapping[str, str], section: StringTable
) -> CheckResult:
    getit = False
    inv_key = params["inv_key"]
    inv_val = params["inv_val"]
    for line in section:
        if len(line) == 2:
            key, val = (i.strip() for i in line)
            if key == "DatabaseName" and val == item:
                getit = True
            elif getit and key == inv_key:
                if val == inv_val:
                    state = State.OK
                    infotxt = f"{inv_key} is {val}"
                else:
                    state = State.WARN
                    infotxt = f"{inv_key} changed from {inv_val} to {val}"
                yield Result(state=state, summary=infotxt)
                return


check_plugin_msexch_dag_dbcopy = CheckPlugin(
    name="msexch_dag_dbcopy",
    service_name="Exchange DAG DBCopy for %s",
    sections=["msexch_dag"],
    discovery_function=discover_msexch_dag_dbcopy,
    check_function=check_msexch_dag_dbcopy,
    check_default_parameters={},
)

# .
#   .--contentindex--------------------------------------------------------.
#   |                      _             _   _           _                 |
#   |       ___ ___  _ __ | |_ ___ _ __ | |_(_)_ __   __| | _____  __      |
#   |      / __/ _ \| '_ \| __/ _ \ '_ \| __| | '_ \ / _` |/ _ \ \/ /      |
#   |     | (_| (_) | | | | ||  __/ | | | |_| | | | | (_| |  __/>  <       |
#   |      \___\___/|_| |_|\__\___|_| |_|\__|_|_| |_|\__,_|\___/_/\_\      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_msexch_dag_contentindex(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0].strip() == "DatabaseName":
            yield Service(item=line[1].strip())


def check_msexch_dag_contentindex(item: str, section: StringTable) -> CheckResult:
    getit = False
    for line in section:
        if len(line) == 2:
            key, val = (i.strip() for i in line)
            if key == "DatabaseName" and val == item:
                getit = True
            elif getit and key == "ContentIndexState":
                if val == "Healthy":
                    state = State.OK
                else:
                    state = State.WARN
                yield Result(state=state, summary="Status: %s" % val)
                return


check_plugin_msexch_dag_contentindex = CheckPlugin(
    name="msexch_dag_contentindex",
    service_name="Exchange DAG ContentIndex of %s",
    sections=["msexch_dag"],
    discovery_function=discover_msexch_dag_contentindex,
    check_function=check_msexch_dag_contentindex,
)

# .
#   .--copyqueue-----------------------------------------------------------.
#   |                                                                      |
#   |           ___ ___  _ __  _   _  __ _ _   _  ___ _   _  ___           |
#   |          / __/ _ \| '_ \| | | |/ _` | | | |/ _ \ | | |/ _ \          |
#   |         | (_| (_) | |_) | |_| | (_| | |_| |  __/ |_| |  __/          |
#   |          \___\___/| .__/ \__, |\__, |\__,_|\___|\__,_|\___|          |
#   |                   |_|    |___/    |_|                                |
#   +----------------------------------------------------------------------+


def discover_msexch_dag_copyqueue(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0].strip() == "DatabaseName":
            yield Service(item=line[1].strip())


def check_msexch_dag_copyqueue(
    item: str, params: Mapping[str, tuple[float, float]], section: StringTable
) -> CheckResult:
    getit = False
    for line in section:
        if len(line) == 2:
            key, val = (i.strip() for i in line)
            if key == "DatabaseName" and val == item:
                getit = True
            elif getit and key == "CopyQueueLength":
                yield from check_levels(
                    int(val),
                    metric_name="length",
                    levels_upper=("fixed", params["levels"]),
                    render_func=str,
                    boundaries=(0, None),
                    label="Queue length",
                )
                return


check_plugin_msexch_dag_copyqueue = CheckPlugin(
    name="msexch_dag_copyqueue",
    service_name="Exchange DAG CopyQueue of %s",
    sections=["msexch_dag"],
    discovery_function=discover_msexch_dag_copyqueue,
    check_function=check_msexch_dag_copyqueue,
    check_default_parameters={"levels": (100, 200)},
    check_ruleset_name="msexch_copyqueue",
)
