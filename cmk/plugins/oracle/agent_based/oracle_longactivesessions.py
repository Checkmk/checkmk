#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<oracle_longactivesessions:seq(124)>>>
# instance_name | sid | serial | machine | process | osuser | program | last_call_el | sql_id

# Columns:
# ORACLE_SID serial# machine process osuser program last_call_el sql_id


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
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

type _SessionRows = list[Sequence[str]]
type Section = Mapping[str, Parsed[_SessionRows]]


def parse_oracle_longactivesessions(string_table: StringTable) -> Section:
    rows_by_sid: dict[str, _SessionRows] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if len(line) > 1:
                    rows_by_sid.setdefault(line[0], []).append(line)

    parsed: dict[str, Parsed[_SessionRows]] = {
        sid: Ok(rows) for sid, rows in rows_by_sid.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_longactivesessions(section: Section) -> DiscoveryResult:
    for sid, result in section.items():
        if isinstance(result, Ok):
            yield from (Service(item=sid) for _line in result.value)


def check_oracle_longactivesessions(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("no info from database. Check ORA %s Instance" % item)
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(rows):
            yield from _check_longactivesessions(params, rows)


def _check_longactivesessions(params: Mapping[str, Any], rows: _SessionRows) -> CheckResult:
    sessioncount = 0
    longoutput: None | str = None

    for line in rows:
        if line[1] != "":
            sessioncount += 1
            _sid, sidnr, serial, machine, process, osuser, program, last_call_el, sql_id = line

            longoutput = f"Session (sid,serial,proc) {sidnr} {serial} {process} active for {render.timespan(int(last_call_el))} from {machine} osuser {osuser} program {program} sql_id {sql_id} "

    yield from check_levels(
        sessioncount,
        metric_name="count",
        levels_upper=("fixed", params["levels"]),
        render_func=str,
    )
    if longoutput:
        yield Result(state=State.OK, notice=longoutput)


agent_section_oracle_longactivesessions = AgentSection(
    name="oracle_longactivesessions",
    parse_function=parse_oracle_longactivesessions,
)


check_plugin_oracle_longactivesessions = CheckPlugin(
    name="oracle_longactivesessions",
    service_name="ORA %s Long Active Sessions",
    discovery_function=discover_oracle_longactivesessions,
    check_function=check_oracle_longactivesessions,
    check_ruleset_name="oracle_longactivesessions",
    check_default_parameters={
        "levels": (500, 1000),
    },
)
