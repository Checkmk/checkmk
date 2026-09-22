#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
    StringTable,
)

from .liboracle import classify_line, Error, Ok, Parsed

# actual format
# <<<oracle_rman>>>
# TUX2|COMPLETED|2015-01-02_07:05:59|2015-01-02_07:05:59|DB_INCR|2|335|8485138
#
# old format
# <<<oracle_rman>>>
# TUX2 COMPLETED 2014-07-08_17:27:59 2014-07-08_17:29:35 DB_INCR 32
# TUX2 COMPLETED 2014-07-08_17:30:02 2014-07-08_17:30:06 ARCHIVELOG 121

# Columns: SID STATUS START END BACKUPTYPE BACKUPAGE

# Create DB_INCR_<Level> checks when parameter is True
# Set this to False for old behavior. This is required for the service
# discovery and can't be set as a inventory parameter.
# This will be removed in a later version of Checkmk. Don't use it for new installations!
inventory_oracle_rman_incremental_details = True


class SectionSidOracleRman(TypedDict):
    sid: str
    backuptype: str
    backuplevel: str
    backupage: int | None
    status: str
    backupscn: int
    used_incr_0: bool


# The backups of one database, keyed by item ("<database>.<backup type>").
SectionOracleRman = dict[str, SectionSidOracleRman]

type Section = Mapping[str, Parsed[SectionOracleRman]]


def parse_oracle_rman(string_table: StringTable) -> Section:
    backups_by_database: dict[str, SectionOracleRman] = {}
    errors: dict[str, str] = {}

    for line in string_table:
        match classify_line(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if (backup := _parse_backup(line)) is not None:
                    item, data = backup
                    # Backups can occur multiple times for the same item. The lines are
                    # already ordered by the DB, meaning that the entry that overwrites the
                    # previous is always the latest backup.
                    backups_by_database.setdefault(line[0], {})[item] = data

    for backups in backups_by_database.values():
        _use_newer_incr_0(backups)

    parsed: dict[str, Parsed[SectionOracleRman]] = {
        name: Ok(backups) for name, backups in backups_by_database.items() if name not in errors
    }
    for name, message in errors.items():
        parsed[name] = Error(message)
    return parsed


def _parse_backup(line: Sequence[str]) -> tuple[str, SectionSidOracleRman] | None:
    backupscn = -1

    if len(line) == 6:
        sid, status, _start, _end, backuptype, backupage_str = line
        item = f"{sid}.{backuptype}"
        backuplevel = "-1"

    elif len(line) == 8:
        (
            sid,
            status,
            _not_used_1,
            _end,
            backuptype,
            backuplevel,
            backupage_str,
            backupscn_str,
        ) = line
        backupscn = -1 if backupscn_str == "" else int(backupscn_str)

        if backuptype == "DB_INCR":
            if inventory_oracle_rman_incremental_details:
                item = f"{sid}.{backuptype}_{backuplevel}"
            else:
                # This is for really old plugins without an information for the backuplevel
                item = f"{sid}.{backuptype}"
        else:
            item = f"{sid}.{backuptype}"

    else:
        return None

    try:
        # sysdate can be old on slow databases with long running SQLs, therefore we can end up
        # with a negative number here if the Archivelog backup is running while the agent is
        # collecting data
        backupage: int | None = max(
            int(backupage_str),
            0,
        )
    except ValueError, TypeError:
        backupage = None

    return item, {
        "sid": sid,
        "backuptype": backuptype,
        "backuplevel": backuplevel,
        "backupage": backupage,
        "status": status,
        "backupscn": backupscn,
        "used_incr_0": False,  # True when last incr0 is newer then incr1
    }


def _use_newer_incr_0(backups: SectionOracleRman) -> None:
    # some tweaks in section for change in behavior of oracle
    # correct backupage for INCR_1 when newer INCR_0 is existing
    for elem in backups:
        # search DB_INCR_1 in section
        if elem.rsplit(".", 1)[1] == "DB_INCR_1":
            # check backupage
            sid_level0 = "%s0" % (elem[0:-1])
            if sid_level0 in backups:
                sid_level0_backupage = backups[sid_level0]["backupage"]
                section_backupage = backups[elem]["backupage"]

                if (
                    isinstance(sid_level0_backupage, int)
                    and isinstance(section_backupage, int)
                    and sid_level0_backupage < section_backupage
                ):
                    backups[elem].update(
                        {
                            "backupage": sid_level0_backupage,
                            "used_incr_0": True,
                        }
                    )


agent_section_oracle_rman = AgentSection(
    name="oracle_rman",
    parse_function=parse_oracle_rman,
)


def discovery_oracle_rman(section: Section) -> DiscoveryResult:
    for result in section.values():
        if not isinstance(result, Ok):
            continue
        for elem in result.value.values():
            sid = elem["sid"]
            backuptype = elem["backuptype"]
            backuplevel = elem["backuplevel"]

            if backuptype in ("ARCHIVELOG", "DB_FULL", "DB_INCR", "CONTROLFILE"):
                if inventory_oracle_rman_incremental_details and backuptype == "DB_INCR":
                    yield Service(item=f"{sid}.{backuptype}_{backuplevel}")
                    continue
                yield Service(item=f"{sid}.{backuptype}")


def _database_of(item: str, section: Section) -> Parsed[SectionOracleRman] | None:
    # "SID.DB_INCR_0" and "SID.ARCHIVELOG" belong to "SID"
    return section.get(item.rsplit(".", 1)[0])


def check_oracle_rman(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    match _database_of(item, section):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed. Working on %s" % item)
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(backups):
            yield from _check_backup(item, params, backups)


def _check_backup(item: str, params: Mapping[str, Any], backups: SectionOracleRman) -> CheckResult:
    rman_backup = backups.get(item)

    sid_level0 = ""

    if not rman_backup:
        # some versions of Oracle removes the last Level 1 after a new Level 0
        # => we have no Level 1 in agent output. level 1 is shown as level 0

        sid_level0 = "%s0" % (item[0:-1])

        if item[-1] == "1" and sid_level0 in backups:
            # => INCR_1 in item and INCR_0 found
            # => Switch to INCR_0 + used_incr_0
            rman_backup = backups[sid_level0]
            rman_backup.update({"used_incr_0": True})

        else:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed. Working on %s" % item)

    status = rman_backup["status"]
    backupage = rman_backup["backupage"]
    backupscn = rman_backup["backupscn"]

    if status in ("COMPLETED", "COMPLETED WITH WARNINGS"):
        if backupage is None:
            # backupage in agent was empty. That's only possible with really old agents.
            yield Result(
                state=State.UNKNOWN,
                summary="Unknown backupage in check found. Please update agent.",
            )

        else:
            # backupage is time in minutes from agent!
            yield from check_levels_v1(
                backupage * 60,
                levels_upper=params.get("levels", (None, None)),
                metric_name="age",
                render_func=render.timespan,
                label="Time since last backup",
            )

        if backupscn > 0:
            yield Result(state=State.OK, summary="Incremental SCN %i" % backupscn)

        if rman_backup["used_incr_0"]:
            yield Result(state=State.OK, summary="Last DB_INCR_0 used")
    else:
        yield Result(
            state=State.CRIT,
            summary="no COMPLETED backup found in last 14 days (very old plug-in in use?)",
        )


def cluster_check_oracle_rman(
    item: str, params: Mapping[str, Any], section: Mapping[str, Section | None]
) -> CheckResult:
    databases: list[Parsed[SectionOracleRman]] = []
    for node_section in section.values():
        if node_section is None:
            continue
        if (database := _database_of(item, node_section)) is not None:
            databases.append(database)

    with_item = [
        database.value
        for database in databases
        if isinstance(database, Ok) and item in database.value
    ]
    if not with_item:
        for database in databases:
            if isinstance(database, Error):
                yield Result(state=State.UNKNOWN, summary=database.message)
                return
        return

    youngest_backup_age: int | None = None
    # take the most current backupage in clustered environments
    for backups in with_item:
        backupage = backups[item]["backupage"]
        if not youngest_backup_age:
            youngest_backup_age = backupage
        if (
            isinstance(backupage, int)
            and isinstance(youngest_backup_age, int)
            and backupage < youngest_backup_age
        ):
            youngest_backup_age = backupage

    # Check only first found item
    first = with_item[0]
    if isinstance(youngest_backup_age, int):
        first[item].update({"backupage": youngest_backup_age})
    yield from _check_backup(item, params, first)


check_plugin_oracle_rman = CheckPlugin(
    name="oracle_rman",
    discovery_function=discovery_oracle_rman,
    service_name="ORA %s RMAN Backup",
    check_function=check_oracle_rman,
    check_ruleset_name="oracle_rman",
    check_default_parameters={},
    cluster_check_function=cluster_check_oracle_rman,
)
