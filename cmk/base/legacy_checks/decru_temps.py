#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature, fahrenheit_to_celsius
from cmk.plugins.decru.lib import DETECT_DECRU

check_info = {}


def discover_decru_temps(info):
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


def parse_decru_temps(string_table: StringTable) -> StringTable:
    return string_table


check_info["decru_temps"] = LegacyCheckDefinition(
    name="decru_temps",
    parse_function=parse_decru_temps,
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.4.1",
        oids=["2", "3"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_decru_temps,
    check_function=check_decru_temps,
    check_ruleset_name="temperature",
)
