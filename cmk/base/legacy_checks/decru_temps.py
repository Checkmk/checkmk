#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature, fahrenheit_to_celsius
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.decru import DETECT_DECRU


def inventory_decru_temps(info):
    for name, rawtemp in info:
        rawtemp = int(fahrenheit_to_celsius(rawtemp))
        # device doesn't provide warning/critical levels
        # instead, this uses the temperature at inventory-time +4/+8
        yield name, {"levels": (rawtemp + 4, rawtemp + 8)}


def check_decru_temps(item, params, info):
    for name, rawtemp in info:
        if name == item:
            temp = fahrenheit_to_celsius(int(rawtemp))
            return check_temperature(temp, params, "decru_temps_%s" % item)
    return None


check_info["decru_temps"] = LegacyCheckDefinition(
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.4.1",
        oids=["2", "3"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_decru_temps,
    check_function=check_decru_temps,
    check_ruleset_name="temperature",
)
