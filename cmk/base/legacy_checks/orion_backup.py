#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_orion_backup(info):
    return [(None, {})]


def check_orion_backup(item, params, info):
    map_states = {
        "1": (1, "inactive"),
        "2": (0, "OK"),
        "3": (1, "occured"),
        "4": (2, "fail"),
    }

    backup_time_status, backup_time = info[0]
    state, state_readable = map_states[backup_time_status]
    return state, f"Status: {state_readable}, Expected time: {backup_time} minutes"


def parse_orion_backup(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["orion_backup"] = LegacyCheckDefinition(
    name="orion_backup",
    parse_function=parse_orion_backup,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.5.3.3",
        oids=["2", "3"],
    ),
    service_name="Backup",
    discovery_function=discover_orion_backup,
    check_function=check_orion_backup,
)
