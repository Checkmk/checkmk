#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.humidity import check_humidity

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def inventory_apc_humidity(info):
    for line in info:
        if int(line[1]) >= 0:
            yield line[0], {}


def check_apc_humidity(item, params, info):
    for line in info:
        if line[0] == item:
            return check_humidity(saveint(line[1]), params)
    return None


def parse_apc_humidity(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_humidity"] = LegacyCheckDefinition(
    name="apc_humidity",
    parse_function=parse_apc_humidity,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.2.3.1",
        oids=["3", "6"],
    ),
    service_name="Humidity %s",
    discovery_function=inventory_apc_humidity,
    check_function=check_apc_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)
