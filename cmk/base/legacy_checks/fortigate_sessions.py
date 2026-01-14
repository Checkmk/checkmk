#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, exists, not_exists, SNMPTree, StringTable

check_info = {}


def discover_fortigate_sessions(info):
    return [(None, {})]


def check_fortigate_sessions(item, params, info):
    try:
        sessions = int(info[0][0])
    except (IndexError, ValueError):
        return

    yield check_levels(
        sessions, "session", params["levels"], human_readable_func=str, infoname="Sessions"
    )


def parse_fortigate_sessions(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["fortigate_sessions"] = LegacyCheckDefinition(
    name="fortigate_sessions",
    parse_function=parse_fortigate_sessions,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.1.10.0"),
        not_exists(".1.3.6.1.4.1.12356.101.4.1.8.0"),
    ),
    # uses mib FORTINET-MIB-280,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["10"],
    ),
    service_name="Sessions",
    discovery_function=discover_fortigate_sessions,
    check_function=check_fortigate_sessions,
    check_ruleset_name="fortigate_sessions",
    check_default_parameters={"levels": (100000, 150000)},
)
