#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import Any

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_average,
    get_rate,
    get_value_store,
)

from cmk.agent_based.v2 import contains, SNMPTree


def parse_pfsense_if(string_table):
    parsed = {}
    for line in string_table:
        parsed[line[0]] = {"ip4_in_blocked": int(line[1])}
    return parsed


def inventory_pfsense_if(parsed):
    for item in parsed:
        yield item, {}


def check_firewall_if(item, params, section):
    if (data := section.get(item)) is None:
        return

    infotext_names = {
        "ip4_in_blocked": "Incoming IPv4 packets blocked: ",
    }

    this_time = time.time()
    value_store = get_value_store()

    for what, counter in data.items():
        rate = get_rate(
            get_value_store(),
            what,
            this_time,
            counter,
            raise_overflow=True,
        )

        if params.get("averaging"):
            backlog_minutes = params["averaging"]
            avgrate = get_average(
                value_store,
                f"firewall_if-{what}.{item}",
                this_time,
                rate,
                backlog_minutes,
            )
            check_against = avgrate
        else:
            check_against = rate

        status, infotext, extraperf = check_levels(
            check_against,
            what,
            params.get(what),
            human_readable_func=lambda x: "%.2f pkts/s" % x,
            infoname=infotext_names[what],
        )

        perfdata: list[Any]
        perfdata = [(what, rate)] + extraperf[:1]

        yield status, infotext, perfdata


check_info["pfsense_if"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1.8.2.1",
        oids=["2", "12"],
    ),
    parse_function=parse_pfsense_if,
    service_name="Firewall Interface %s",
    discovery_function=inventory_pfsense_if,
    check_function=check_firewall_if,
    check_ruleset_name="firewall_if",
    check_default_parameters={
        "ipv4_in_blocked": (100.0, 10000.0),
        "average": 3,
    },
)
