#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

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
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs, Section

# <<<db2_backup>>>
# [[[db2taddm:CMDBS1]]]
# 2015-03-12-04.00.13.000000


def discover_db2_backup(section: Section) -> DiscoveryResult:
    for instance in section[1]:
        yield Service(item=instance)


def check_db2_backup(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    db = section[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    try:
        last_backup = time.mktime(time.strptime(db[0][0][:19], "%Y-%m-%d-%H.%M.%S"))
    except Exception:
        if db[0][0] == "-":
            yield Result(state=State.WARN, summary="No backup available")
        else:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Last backup contains an invalid timestamp: {db[0][0]}",
            )
        return

    age = time.time() - last_backup
    yield from check_levels_v1(
        age,
        levels_upper=params["levels"],
        render_func=render.timespan,
        label="Time since last backup",
    )


agent_section_db2_backup = AgentSection(
    name="db2_backup",
    parse_function=parse_db2_dbs,
)


check_plugin_db2_backup = CheckPlugin(
    name="db2_backup",
    service_name="DB2 Backup %s",
    discovery_function=discover_db2_backup,
    check_function=check_db2_backup,
    check_ruleset_name="db2_backup",
    check_default_parameters={
        "levels": (86400 * 14, 86400 * 28),
    },
)
