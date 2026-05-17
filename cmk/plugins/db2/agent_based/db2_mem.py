#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
    StringTable,
)


def parse_db2_mem(string_table: StringTable) -> StringTable:
    return string_table


def discover_db2_mem(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0] == "Instance":
            yield Service(item=line[1])


def check_db2_mem(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        raise IgnoreResultsError("Login into database failed")

    in_block = False
    limit: int | None = None
    usage: int | None = None
    for line in section:
        if line[1] == item:
            in_block = True
        elif in_block is True:
            if line[-1].lower() == "kb":
                value = int(line[-2]) * 1024
            elif line[-1].lower() == "mb":
                value = int(line[-2]) * 1024 * 1024
            else:
                value = int(line[-2])

            if limit is None:
                limit = value
            else:
                usage = value
                break

    if limit is None or usage is None:
        return

    perc_free = (limit - usage) / limit * 100.0
    yield Result(state=State.OK, summary=f"Max {render.bytes(limit)}")
    yield from check_levels_v1(
        usage,
        metric_name="mem_used",
        render_func=render.bytes,
        label="Used",
        boundaries=(0, limit),
    )
    yield from check_levels_v1(
        perc_free,
        levels_lower=params["levels_lower"],
        render_func=render.percent,
        label="Free",
    )


agent_section_db2_mem = AgentSection(
    name="db2_mem",
    parse_function=parse_db2_mem,
)


check_plugin_db2_mem = CheckPlugin(
    name="db2_mem",
    service_name="Memory %s",
    discovery_function=discover_db2_mem,
    check_function=check_db2_mem,
    check_ruleset_name="db2_mem",
    check_default_parameters={"levels_lower": (10.0, 5.0)},
)
