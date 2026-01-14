#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.domino.lib import DETECT

check_info = {}


def discover_domino_transactions(info):
    if info:
        yield None, {}


def check_domino_transactions(_no_item, params, info):
    if info:
        yield check_levels(
            int(info[0][0]),
            "transactions",
            params["levels"],
            human_readable_func=str,
            infoname="Transactions per minute (avg)",
        )


def parse_domino_transactions(string_table: StringTable) -> StringTable:
    return string_table


check_info["domino_transactions"] = LegacyCheckDefinition(
    name="domino_transactions",
    parse_function=parse_domino_transactions,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["2"],
    ),
    service_name="Domino Server Transactions",
    discovery_function=discover_domino_transactions,
    check_function=check_domino_transactions,
    check_ruleset_name="domino_transactions",
    check_default_parameters={"levels": (30000, 35000)},
)
