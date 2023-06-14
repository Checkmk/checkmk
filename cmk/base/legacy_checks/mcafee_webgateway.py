#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, get_rate, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mcafee_gateway import inventory_mcafee_gateway_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

# -- Statistics
# .1.3.6.1.4.1.1230.2.7.2.1.2.0 200 --> MCAFEE-MWG-MIB::stMalwareDetected.0
# .1.3.6.1.4.1.1230.2.7.2.1.5.0 4394370 --> MCAFEE-MWG-MIB::stConnectionsBlocked.0


def parse_mcaffee_webgateway(info):
    parsed = []
    for index, key, label in (
        (0, "infections", "Infections"),
        (1, "connections_blocked", "Connections blocked"),
    ):
        try:
            parsed.append((key, int(info[0][index]), label))
        except (IndexError, ValueError):
            pass
    return parsed


def check_mcafee_webgateway(_no_item, params, parsed):
    now = time.time()
    for key, value, label in parsed:
        rate = get_rate("check_mcafee_webgateway.%s" % key, now, value)
        yield check_levels(
            rate,
            "%s_rate" % key,
            params.get(key),
            human_readable_func=lambda f: "%.1f/s" % f,
            infoname=label,
        )


check_info["mcafee_webgateway"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "mcafee web gateway"),
    parse_function=parse_mcaffee_webgateway,
    discovery_function=inventory_mcafee_gateway_generic,
    check_function=check_mcafee_webgateway,
    service_name="Web gateway statistics",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.1",
        oids=["2", "5"],
    ),
    check_ruleset_name="mcafee_web_gateway",
)
