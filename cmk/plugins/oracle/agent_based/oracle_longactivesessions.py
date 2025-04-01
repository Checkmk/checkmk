#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_longactivesessions:seq(124)>>>
# instance_name | sid | serial | machine | process | osuser | program | last_call_el | sql_id

# Columns:
# ORACLE_SID serial# machine process osuser program last_call_el sql_id


from collections.abc import Mapping
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


def inventory_oracle_longactivesessions(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_oracle_longactivesessions(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    sessioncount = 0
    itemfound = False
    longoutput: None | str = None

    for line in section:
        if len(line) <= 1 or line[0] != item:
            continue

        itemfound = True
        if line[1] != "":
            sessioncount += 1
            _sid, sidnr, serial, machine, process, osuser, program, last_call_el, sql_id = line

            longoutput = f"Session (sid,serial,proc) {sidnr} {serial} {process} active for {render.timespan(int(last_call_el))} from {machine} osuser {osuser} program {program} sql_id {sql_id} "

    if not itemfound:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("no info from database. Check ORA %s Instance" % item)

    yield from check_levels(
        sessioncount,
        metric_name="count",
        levels_upper=("fixed", params["levels"]),
        render_func=str,
    )
    if longoutput:
        yield Result(state=State.OK, notice=longoutput)


def parse_oracle_longactivesessions(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_longactivesessions = AgentSection(
    name="oracle_longactivesessions",
    parse_function=parse_oracle_longactivesessions,
)


check_plugin_oracle_longactivesessions = CheckPlugin(
    name="oracle_longactivesessions",
    service_name="ORA %s Long Active Sessions",
    discovery_function=inventory_oracle_longactivesessions,
    check_function=check_oracle_longactivesessions,
    check_ruleset_name="oracle_longactivesessions",
    check_default_parameters={
        "levels": (500, 1000),
    },
)
