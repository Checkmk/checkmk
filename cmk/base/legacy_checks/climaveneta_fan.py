#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import equals, LegacyCheckDefinition
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def inventory_climaveneta_fan(info):
    if len(info[0]) == 2:
        return [("1", {}), ("2", {})]
    return []


def check_climaveneta_fan(item, params, info):
    rpm = int(info[0][int(item) - 1])
    return check_fan(rpm, params)


check_info["climaveneta_fan"] = LegacyCheckDefinition(
    detect=equals(".1.3.6.1.2.1.1.1.0", "pCO Gateway"),
    check_function=check_climaveneta_fan,
    discovery_function=inventory_climaveneta_fan,
    service_name="Fan %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1.2",
        oids=["42", "43"],
    ),
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (200, 100),
    },
)
