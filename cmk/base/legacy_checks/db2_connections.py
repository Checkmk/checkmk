#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

check_info = {}

# <<<db2_connections>>>
# [[[db2taddm:CMDBS1]]]
# port 50214
# sessions 40
# latency 0:1.03


def discover_db2_connections(parsed):
    for item in parsed[1]:
        yield item, None


def check_db2_connections(item, params, parsed):
    db = parsed[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    data = dict(db)

    yield check_levels(
        int(data["connections"]),
        "connections",
        params["levels_total"],
        infoname="Connections",
    )

    yield 0, "Port: %s" % data["port"]

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

        yield 0, "Latency: %.2f ms" % ms, [("latency", ms)]


check_info["db2_connections"] = LegacyCheckDefinition(
    name="db2_connections",
    parse_function=parse_db2_dbs,
    service_name="DB2 Connections %s",
    discovery_function=discover_db2_connections,
    check_function=check_db2_connections,
    check_ruleset_name="db2_connections",
    check_default_parameters={
        "levels_total": (150, 200),
    },
)
