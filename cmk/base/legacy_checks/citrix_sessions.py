#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<citrix_sessions>>>
# sessions 1
# active_sessions 1
# inactive_sessions 0


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}

citrix_sessions_default_levels = {
    "total": (60, 65),
    "active": (60, 65),
    "inactive": (10, 15),
}


def discover_citrix_sessions(info):
    return [(None, citrix_sessions_default_levels)]


def check_citrix_sessions(_no_item, params, info):
    session = {}
    for line in info:
        if len(line) > 1:
            session.setdefault(line[0], int(line[1]))

    if not session:
        yield 3, "Could not collect session information. Please check the agent configuration."
        return

    for key, what in [
        ("sessions", "total"),
        ("active_sessions", "active"),
        ("inactive_sessions", "inactive"),
    ]:
        if session.get(key) is None:
            continue
        yield check_levels(
            session[key],
            what,
            params.get(what),
            infoname=what.title(),
        )


def parse_citrix_sessions(string_table: StringTable) -> StringTable:
    return string_table


check_info["citrix_sessions"] = LegacyCheckDefinition(
    name="citrix_sessions",
    parse_function=parse_citrix_sessions,
    service_name="Citrix Sessions",
    discovery_function=discover_citrix_sessions,
    check_function=check_citrix_sessions,
    check_ruleset_name="citrix_sessions",
)
