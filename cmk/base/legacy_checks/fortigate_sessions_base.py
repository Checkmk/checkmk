#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, exists, SNMPTree, StringTable

check_info = {}


def discover_fortigate_sessions_base(info):
    yield None, {}


def check_fortigate_sessions_base(item, params, info):
    sessions = int(info[0][0])
    yield check_levels(
        sessions, "session", params["levels"], human_readable_func=str, infoname="Sessions"
    )


def parse_fortigate_sessions_base(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["fortigate_sessions_base"] = LegacyCheckDefinition(
    name="fortigate_sessions_base",
    parse_function=parse_fortigate_sessions_base,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.101.4.1.8.0"),
    ),
    # uses mib FORTINET-FORTIGATE-MIB,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.1",
        oids=["8"],
    ),
    service_name="Sessions",
    discovery_function=discover_fortigate_sessions_base,
    check_function=check_fortigate_sessions_base,
    check_ruleset_name="fortigate_sessions",
    check_default_parameters={"levels": (100000, 150000)},
)
