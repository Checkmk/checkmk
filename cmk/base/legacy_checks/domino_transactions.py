#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.domino import DETECT

domino_transactions_default_levels = (30000, 35000)


def inventory_domino_transactions(info):
    if info:
        yield None, domino_transactions_default_levels


def check_domino_transactions(_no_item, params, info):
    if info:
        reading = int(info[0][0])
        warn, crit = params
        infotext = "Transactions per minute (avg): %s" % reading
        levels = f" (Warn/Crit at {warn}/{crit})"
        perfdata = [("transactions", reading, warn, crit)]
        state = 0
        if reading >= crit:
            state = 2
            infotext += levels
        elif reading >= warn:
            state = 1
            infotext += levels
        yield state, infotext, perfdata


check_info["domino_transactions"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["2"],
    ),
    service_name="Domino Server Transactions",
    discovery_function=inventory_domino_transactions,
    check_function=check_domino_transactions,
    check_ruleset_name="domino_transactions",
)
