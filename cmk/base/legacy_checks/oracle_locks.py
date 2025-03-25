#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.oracle import oracle_handle_ora_errors

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render, StringTable

check_info = {}

# <<<oracle_locks>>>
# TUX12C|273|2985|ora12c.local|sqlplus@ora12c.local (TNS V1-V3)|46148|oracle|633|NULL|NULL
# newdb|25|15231|ol6131|sqlplus@ol6131 (TNS V1-V3)|13275|oracle|SYS|3782|VALID|1|407|1463|ol6131|sqlplus@ol6131 (TNS V1-V3)|13018|oracle|SYS


def inventory_oracle_locks(info):
    return [(line[0], {}) for line in info if len(line) >= 10]


def check_oracle_locks(item, params, info):
    lockcount = 0
    state = -1
    infotext = ""

    for line in info:
        warn, crit = params["levels"]
        if line[0] == item and line[1] != "":
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            if isinstance(err, tuple):
                return err

            if len(line) == 10:
                # old format from locks_old in current plugin
                (
                    _sid,
                    sidnr,
                    serial,
                    machine,
                    _program,
                    process,
                    osuser,
                    ctime,
                    object_owner,
                    object_name,
                ) = line

            elif len(line) == 18:
                (
                    _sid,
                    sidnr,
                    serial,
                    machine,
                    _program,
                    process,
                    osuser,
                    _dbusername,
                    ctime,
                    _block_status,
                    _blk_inst_id,
                    _blk_sid,
                    _blk_serial,
                    _blk_machine,
                    _blk_program,
                    _blk_process,
                    _blk_osuser,
                    _blk_dbusername,
                ) = line

                object_owner = ""
                object_name = ""

            else:
                raise IgnoreResultsError("Unknow number of items in agent output")

            ctime = int(ctime)

            if not crit and not warn:
                infotext += f"locktime {render.time_offset(ctime)} Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "
            elif ctime >= crit:
                state = 2
                lockcount += 1
                infotext += f"locktime {render.time_offset(ctime)} (!!) Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "

            elif ctime >= warn:
                state = max(1, state)
                lockcount += 1
                infotext += f"locktime {render.time_offset(ctime)} (!) Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "

        if line[0] == item and line[1] == "":
            state = max(0, state)

    if infotext == "":
        infotext = "No locks existing"
    elif lockcount > 10:
        infotext = "more then 10 locks existing!"

    if state != -1:
        return (state, infotext)

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_locks(string_table: StringTable) -> StringTable:
    return string_table


check_info["oracle_locks"] = LegacyCheckDefinition(
    name="oracle_locks",
    parse_function=parse_oracle_locks,
    service_name="ORA %s Locks",
    discovery_function=inventory_oracle_locks,
    check_function=check_oracle_locks,
    check_ruleset_name="oracle_locks",
    check_default_parameters={
        "levels": (1800, 3600),
    },
)
