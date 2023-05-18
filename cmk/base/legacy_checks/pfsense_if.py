#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import contains, LegacyCheckDefinition
from cmk.base.check_legacy_includes.firewall_if import check_firewall_if
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def parse_pfsense_if(info):
    parsed = {}
    for line in info:
        parsed[line[0]] = {"ip4_in_blocked": int(line[1])}
    return parsed


def inventory_pfsense_if(parsed):
    for item in parsed:
        yield item, {}


check_info["pfsense_if"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    parse_function=parse_pfsense_if,
    discovery_function=inventory_pfsense_if,
    check_function=check_firewall_if,
    service_name="Firewall Interface %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1.8.2.1",
        oids=["2", "12"],
    ),
    check_ruleset_name="firewall_if",
    check_default_parameters={
        "ipv4_in_blocked": (100.0, 10000.0),
        "average": 3,
    },
)
