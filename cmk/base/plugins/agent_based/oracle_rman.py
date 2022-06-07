#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping, Optional, TypedDict

from .agent_based_api.v1 import check_levels, IgnoreResultsError, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import oracle

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

SectionSidOracleRman = TypedDict(
    "SectionSidOracleRman",
    {
        "sid": str,
        "backuptype": str,
        "backuplevel": str,
        "backupage": Optional[int],
        "status": str,
        "backupscn": int,
        "used_incr_0": bool,
    },
)

SectionOracleRman = Dict[str, SectionSidOracleRman]


def parse_oracle_rman(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> SectionOracleRman:
    section: SectionOracleRman = {}
    error_sids = {}

    for line in string_table:
        # Check for query errors
        check_ora = oracle.OraErrors(line)
        if check_ora.ignore:
            continue  # ignore ancient agent outputs
        if check_ora.has_error:
            sid = line[0]
            error_sids[sid] = check_ora.error_text

        # we leave the llop with break when item is found except for DB_INCR_0
        # later we need to restore the values for DB_INCR_0 due to possible
        # overwrite with new line from section

        backupscn = -1
        item = ""

        if len(line) == 6:
            sid, status, _start, _end, backuptype, backupage_str = line
            item = "%s.%s" % (sid, backuptype)

            backupscn = int(-1)
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
            if backupscn_str == "":
                backupscn = int(-1)
            else:
                backupscn = int(backupscn_str)

            if backuptype == "DB_INCR":

                if inventory_oracle_rman_incremental_details:
                    item = "%s.%s_%s" % (sid, backuptype, backuplevel)
                else:
                    # This is for really old plugins without an information for the backuplevel
                    item = "%s.%s" % (sid, backuptype)
            else:
                item = "%s.%s" % (sid, backuptype)

        else:
            continue

        try:
            # sysdate can be old on slow databases with long running SQLs, therefore we can end up
            # with a negative number here if the Archivelog backup is running while the agent is
            # collecting data
            backupage: Optional[int] = max(
                int(backupage_str),
                0,
            )
        except (ValueError, TypeError):
            backupage = None

        # Backups can occur multiple times for the same item. The lines are
        # already ordered by the DB, meaning that the entry that overwrites the
        # previous is always the latest backup.
        section[item] = {
            "sid": sid,
            "backuptype": backuptype,
            "backuplevel": backuplevel,
            "backupage": backupage,
            "status": status,
            "backupscn": backupscn,
            "used_incr_0": False,  # True when last incr0 is newer then incr1
        }

    # some tweaks in section for change in behavior of oracle
    # correct backupage for INCR_1 when newer INCR_0 is existing
    for elem in section:

        # search DB_INCR_1 in section
        if elem.rsplit(".", 1)[1] == "DB_INCR_1":

            # check backupage
            sid_level0 = "%s0" % (elem[0:-1])
            if sid_level0 in section:
                sid_level0_backupage = section[sid_level0]["backupage"]
                section_backupage = section[elem]["backupage"]

                if isinstance(sid_level0_backupage, int) and isinstance(section_backupage, int):
                    if sid_level0_backupage < section_backupage:
                        section[elem].update(
                            {
                                "backupage": sid_level0_backupage,
                                "used_incr_0": True,
                            }
                        )

    return section


register.agent_section(
    name="oracle_rman",
    parse_function=parse_oracle_rman,
)


def discovery_oracle_rman(section: SectionOracleRman) -> DiscoveryResult:
    for elem in section.values():

        sid = elem["sid"]
        backuptype = elem["backuptype"]
        backuplevel = elem["backuplevel"]

        if backuptype in ("ARCHIVELOG", "DB_FULL", "DB_INCR", "CONTROLFILE"):

            if inventory_oracle_rman_incremental_details and backuptype == "DB_INCR":
                yield Service(item="%s.%s_%s" % (sid, backuptype, backuplevel))
                continue
            yield Service(item="%s.%s" % (sid, backuptype))


def check_oracle_rman(
    item: str, params: Mapping[str, Any], section: SectionOracleRman
) -> CheckResult:

    rman_backup = section.get(item)

    sid_level0 = ""

    if not rman_backup:

        # some versions of Oracle removes the last Level 1 after a new Level 0
        # => we have no Level 1 in agent output. level 1 is shown as level 0

        sid_level0 = "%s0" % (item[0:-1])

        if item[-1] == "1" and sid_level0 in section:

            # => INCR_1 in item and INCR_0 found
            # => Switch to INCR_0 + used_incr_0
            rman_backup = section[sid_level0]
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
                state=state.UNKNOWN,
                summary="Unknown backupage in check found. Please update agent.",
            )

        else:
            # backupage is time in minutes from agent!
            yield from check_levels(
                backupage * 60,
                levels_upper=params.get("levels", (None, None)),
                metric_name="age",
                render_func=render.timespan,
                label="Time since last backup",
            )

        if backupscn > 0:
            yield Result(state=state.OK, summary="Incremental SCN %i" % backupscn)

        if rman_backup["used_incr_0"]:
            yield Result(state=state.OK, summary="Last DB_INCR_0 used")
    else:
        yield Result(
            state=state.CRIT,
            summary="no COMPLETED backup found in last 14 days (very old plugin in use?)",
        )


def cluster_check_oracle_rman(
    item: str, params: Mapping[str, Any], section: Mapping[str, Optional[SectionOracleRman]]
) -> CheckResult:

    youngest_backup_age: Optional[int] = None
    # take the most current backupage in clustered environments
    for node_data in section.values():
        if node_data is None:
            continue
        if item not in node_data:
            continue
        backupage = node_data[item]["backupage"]
        if not youngest_backup_age:
            youngest_backup_age = backupage
        if (
            isinstance(backupage, int)
            and isinstance(youngest_backup_age, int)
            and backupage < youngest_backup_age
        ):
            youngest_backup_age = backupage

    # Check only first found item
    for node_data in section.values():
        if node_data is None or item not in node_data:
            continue
        if isinstance(youngest_backup_age, int):
            node_data[item].update({"backupage": youngest_backup_age})
        yield from check_oracle_rman(item, params, node_data)
        return


register.check_plugin(
    name="oracle_rman",
    discovery_function=discovery_oracle_rman,
    service_name="ORA %s RMAN Backup",
    check_function=check_oracle_rman,
    check_ruleset_name="oracle_rman",
    check_default_parameters={},
    cluster_check_function=cluster_check_oracle_rman,
)
