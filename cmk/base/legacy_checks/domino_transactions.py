#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.domino import DETECT


def inventory_domino_transactions(info):
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
    parse_function=parse_domino_transactions,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["2"],
    ),
    service_name="Domino Server Transactions",
    discovery_function=inventory_domino_transactions,
    check_function=check_domino_transactions,
    check_ruleset_name="domino_transactions",
    check_default_parameters={"levels": (30000, 35000)},
)
