#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<<oracle_recovery_state:sep(124)>>>
# TUX2|tux2|PRIMARY|MOUNTED|1|1405456155|ONLINE||NO|2719061
# TUX2|tux2|PRIMARY|MOUNTED|2|1405456155|ONLINE||NO|2719061
# new format with backupmode
# <<<oracle_recovery_status:sep(124)>>>
# TUX2|tux2|PRIMARY|READ WRITE|1|1419771465|317|ONLINE|NO|YES|8149107|NOT ACTIVE|489
# TUX2|tux2|PRIMARY|READ WRITE|2|1419771465|317|ONLINE|NO|YES|8149107|NOT ACTIVE|489

# Databases seem to also report lines with some data missing:
# PV|PV|PRIMARY|READ WRITE|397|1433251398|7297|ONLINE|NO|YES|10740614283
# PV|PV|PRIMARY|READ WRITE|398|1433251398|7297|ONLINE|NO|YES|10740614283
# PV|PV|PRIMARY|READ WRITE|399|||ONLINE|||0
# PV|PV|PRIMARY|READ WRITE|400|||ONLINE|||0
# PV|PV|PRIMARY|READ WRITE|401|||ONLINE|||0

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


def inventory_oracle_recovery_status(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_oracle_recovery_status(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    state = State.OK
    offlinecount = 0
    filemissingcount = 0
    oldest_checkpoint_age: int | None = None

    oldest_backup_age = -1
    backup_count = 0

    perfdata: list[Metric] = []

    itemfound = False
    for line in section:
        if line[0] == item:
            itemfound = True

            if len(line) == 11:
                (
                    db_name,
                    db_unique_name,
                    database_role,
                    _open_mode,
                    _filenr,
                    _checkpoint_time,
                    checkpoint_age,
                    datafilestatus,
                    _recovery,
                    _fuzzy,
                    _checkpoint_change,
                ) = line

                backup_state = "unknown"

            elif len(line) == 13:
                (
                    db_name,
                    db_unique_name,
                    database_role,
                    _open_mode,
                    _filenr,
                    _checkpoint_time,
                    checkpoint_age,
                    datafilestatus,
                    _recovery,
                    _fuzzy,
                    _checkpoint_change,
                    backup_state,
                    backup_age,
                ) = line

            else:
                yield Result(state=State.CRIT, summary=", ".join(line))
                return

            if backup_state == "ACTIVE":
                backup_count += 1
                oldest_backup_age = max(int(backup_age), oldest_backup_age)

            if datafilestatus == "ONLINE":
                if backup_state == "FILE MISSING":
                    filemissingcount += 1
                elif checkpoint_age:
                    checkpoint_age = int(checkpoint_age)  # type: ignore[assignment]

                    if oldest_checkpoint_age is None:
                        oldest_checkpoint_age = int(checkpoint_age)
                    else:
                        oldest_checkpoint_age = max(oldest_checkpoint_age, int(checkpoint_age))

            else:
                offlinecount += 1

    if not itemfound:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    infotext = "%s database" % (database_role.lower())

    if oldest_checkpoint_age is None:
        infotext += ", no online datafiles found(!!)"
        state = State.CRIT

    elif oldest_checkpoint_age <= -1:
        # we found a negative time for last checkpoint
        infotext += (
            ", oldest checkpoint is in the future  %s(!), check the time on the server"
            % render.timespan(int(oldest_checkpoint_age) * -1)
        )
        state = State.worst(state, State.WARN)

    else:
        infotext += ", oldest Checkpoint %s ago" % (render.timespan(int(oldest_checkpoint_age)))

    if (
        (database_role == "PRIMARY" and db_name == "_MGMTDB" and db_unique_name == "_mgmtdb")
        or not params.get("levels")
    ) or db_name[db_name.rfind(".") + 1 :] == "PDB$SEED":
        # We ignore the state of the check when no parameters are known
        # _mgmtdb is new internal instance from 12.1.0.2 on Grid-Infrastructure
        # ignore PDB$SEED because this PDB is always in READ ONLY mode
        if oldest_checkpoint_age is not None:  # for mypy, this seems to have been the case always.
            perfdata.append(Metric("checkpoint_age", oldest_checkpoint_age))
    else:
        warn, crit = params["levels"]
        if database_role == "PRIMARY":
            # checkpoint age should not higher on primary as well
            # There is no CRIT for older checkoint age as this is mostly not a
            # serios issue.
            # otherwise the standby will produca a warning or crit as well
            if oldest_checkpoint_age >= warn:
                infotext += "(!)"
                state = State.worst(state, State.WARN)

            if (
                oldest_checkpoint_age is not None
            ):  # for mypy, this seems to have been the case always.
                perfdata.append(
                    Metric("checkpoint_age", oldest_checkpoint_age, levels=(warn, float("inf")))
                )
        else:
            if (
                oldest_checkpoint_age is not None
            ):  # for mypy, this seems to have been the case always.
                perfdata.append(
                    Metric("checkpoint_age", oldest_checkpoint_age, levels=(warn, crit))
                )

            # check the checkpoint age on a non primary database!
            if oldest_checkpoint_age >= crit:
                infotext += "(!!)"
                state = State.CRIT
            elif oldest_checkpoint_age >= warn:
                infotext += "(!)"
                state = State.worst(state, State.WARN)

        infotext += f" (warn/crit at {render.timespan(warn)}/{render.timespan(crit)} )"

    if offlinecount > 0:
        infotext += " %i datafiles offline(!!)" % (offlinecount)
        state = State.CRIT

    if filemissingcount > 0:
        infotext += " %i missing datafiles(!!)" % (filemissingcount)
        state = State.CRIT

    if oldest_backup_age > 0:
        infotext += " %i datafiles in backup mode oldest is %s" % (
            backup_count,
            render.timespan(oldest_backup_age),
        )

        if params.get("backup_age"):
            warn, crit = params["backup_age"]
            infotext += f" (warn/crit at {render.timespan(warn)}/{render.timespan(crit)})"
            perfdata.append(Metric("backup_age", oldest_backup_age, levels=(warn, crit)))

            if oldest_backup_age >= crit:
                infotext += "(!!)"
                state = State.CRIT
            elif oldest_backup_age >= warn:
                infotext += "(!)"
                state = State.worst(state, State.WARN)
        else:
            perfdata.append(Metric("backup_age", oldest_backup_age))
    else:
        # create a 'dummy' performance data with 0
        # => The age from plug-in is only valid when a datafile is in backup mode!
        perfdata.append(Metric("backup_age", 0))

    yield Result(state=state, summary=infotext)
    yield from perfdata


def parse_oracle_recovery_status(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_recovery_status = AgentSection(
    name="oracle_recovery_status",
    parse_function=parse_oracle_recovery_status,
)


check_plugin_oracle_recovery_status = CheckPlugin(
    name="oracle_recovery_status",
    service_name="ORA %s Recovery Status",
    discovery_function=inventory_oracle_recovery_status,
    check_function=check_oracle_recovery_status,
    check_default_parameters={},
    check_ruleset_name="oracle_recovery_status",
)
