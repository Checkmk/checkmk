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
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs, Section

# <<<db2_connections>>>
# [[[db2taddm:CMDBS1]]]
# port 50214
# sessions 40
# latency 0:1.03


def discover_db2_connections(section: Section) -> DiscoveryResult:
    for item in section[1]:
        yield Service(item=item)


def check_db2_connections(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    db = section[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    data = dict(db)

    yield from check_levels_v1(
        int(data["connections"]),
        metric_name="connections",
        levels_upper=params["levels_total"],
        label="Connections",
    )

    yield Result(state=State.OK, summary=f"Port: {data['port']}")

    if "latency" in data:
        latency = data["latency"]
        if ":" not in latency:
            ms = int(latency)
        else:  # handle old time format: 'min:seconds.milliseconds'
            minutes, rest = data["latency"].split(":")
            # handle different locale settings
            if "," in rest:
                seconds, mseconds = rest.split(",")
            else:
                seconds, mseconds = rest.split(".")
            ms = int(minutes) * 60 * 1000 + int(seconds) * 1000 + int(mseconds)

        yield Result(state=State.OK, summary=f"Latency: {ms:.2f} ms")
        yield Metric("latency", ms)


agent_section_db2_connections = AgentSection(
    name="db2_connections",
    parse_function=parse_db2_dbs,
)


check_plugin_db2_connections = CheckPlugin(
    name="db2_connections",
    service_name="DB2 Connections %s",
    discovery_function=discover_db2_connections,
    check_function=check_db2_connections,
    check_ruleset_name="db2_connections",
    check_default_parameters={
        "levels_total": (150, 200),
    },
)
