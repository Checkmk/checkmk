#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.domino.lib import DETECT

check_info = {}


def discover_domino_users(info):
    if info:
        yield None, {}


def check_domino_users(_no_item, params, info):
    try:
        users = int(info[0][0])
    except IndexError:
        return

    yield check_levels(
        users, "users", params["levels"], human_readable_func=str, infoname="Domino users on server"
    )


def parse_domino_users(string_table: StringTable) -> StringTable:
    return string_table


check_info["domino_users"] = LegacyCheckDefinition(
    name="domino_users",
    parse_function=parse_domino_users,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["6"],
    ),
    service_name="Domino Users",
    discovery_function=discover_domino_users,
    check_function=check_domino_users,
    check_ruleset_name="domino_users",
    check_default_parameters={
        "levels": (1000, 1500),
    },
)
