#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

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

from .liboracle import Error, Ok, oracle_handle_ora_errors, Parsed

# <<<oracle_locks>>>
# TUX12C|273|2985|ora12c.local|sqlplus@ora12c.local (TNS V1-V3)|46148|oracle|633|NULL|NULL
# newdb|25|15231|ol6131|sqlplus@ol6131 (TNS V1-V3)|13275|oracle|SYS|3782|VALID|1|407|1463|ol6131|sqlplus@ol6131 (TNS V1-V3)|13018|oracle|SYS

type _LockRows = list[Sequence[str]]
type Section = Mapping[str, Parsed[_LockRows]]


def parse_oracle_locks(string_table: StringTable) -> Section:
    rows_by_sid: dict[str, _LockRows] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                rows_by_sid.setdefault(line[0], []).append(line)

    parsed: dict[str, Parsed[_LockRows]] = {
        sid: Ok(rows) for sid, rows in rows_by_sid.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_locks(section: Section) -> DiscoveryResult:
    for sid, result in section.items():
        if isinstance(result, Ok):
            yield from (Service(item=sid) for line in result.value if len(line) >= 10)


def check_oracle_locks(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(rows):
            yield from _check_locks(params, rows)


def _check_locks(params: Mapping[str, Any], rows: _LockRows) -> CheckResult:
    lockcount = 0
    state: State | None = None
    infotext = ""
    warn, crit = params["levels"]

    for line in rows:
        if line[1] != "":
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

        if line[1] == "":
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


agent_section_oracle_locks = AgentSection(
    name="oracle_locks",
    parse_function=parse_oracle_locks,
)


check_plugin_oracle_locks = CheckPlugin(
    name="oracle_locks",
    service_name="ORA %s Locks",
    discovery_function=discover_oracle_locks,
    check_function=check_oracle_locks,
    check_ruleset_name="oracle_locks",
    check_default_parameters={
        "levels": (1800, 3600),
    },
)
