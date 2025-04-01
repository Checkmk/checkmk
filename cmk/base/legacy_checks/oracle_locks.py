#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, assert_never

from cmk.base.check_legacy_includes.oracle import oracle_handle_ora_errors

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

# <<<oracle_locks>>>
# TUX12C|273|2985|ora12c.local|sqlplus@ora12c.local (TNS V1-V3)|46148|oracle|633|NULL|NULL
# newdb|25|15231|ol6131|sqlplus@ol6131 (TNS V1-V3)|13275|oracle|SYS|3782|VALID|1|407|1463|ol6131|sqlplus@ol6131 (TNS V1-V3)|13018|oracle|SYS


def inventory_oracle_locks(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=line[0]) for line in section if len(line) >= 10]


def check_oracle_locks(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    lockcount = 0
    state: State | None = None
    infotext = ""

    for line in section:
        warn, crit = params["levels"]
        if line[0] == item and line[1] != "":
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            elif isinstance(err, Result):
                yield err
            elif err is None:
                pass
            else:
                assert_never(err)

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
                    raw_ctime,
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
                    raw_ctime,
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

            ctime = int(raw_ctime)

            if not crit and not warn:
                infotext += f"locktime {render.time_offset(ctime)} Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "
            elif ctime >= crit:
                state = State.CRIT
                lockcount += 1
                infotext += f"locktime {render.time_offset(ctime)} (!!) Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "

            elif ctime >= warn:
                state = State.worst(State.WARN, state or State.OK)
                lockcount += 1
                infotext += f"locktime {render.time_offset(ctime)} (!) Session (sid,serial, proc) {sidnr},{serial},{process} machine {machine} osuser {osuser} object: {object_owner}.{object_name} ; "

        if line[0] == item and line[1] == "":
            state = state or State.OK

    if infotext == "":
        infotext = "No locks existing"
    elif lockcount > 10:
        infotext = "more then 10 locks existing!"

    if state:
        yield Result(state=state, summary=infotext)
        return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_locks(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_locks = AgentSection(
    name="oracle_locks",
    parse_function=parse_oracle_locks,
)


check_plugin_oracle_locks = CheckPlugin(
    name="oracle_locks",
    service_name="ORA %s Locks",
    discovery_function=inventory_oracle_locks,
    check_function=check_oracle_locks,
    check_ruleset_name="oracle_locks",
    check_default_parameters={
        "levels": (1800, 3600),
    },
)
