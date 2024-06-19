#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def inventory_apc_inrow_fanspeed(info):
    if info:
        return [(None, None)]
    return []


def check_apc_inrow_fanspeed(_no_item, _no_params, info):
    value = savefloat(info[0][0]) / 10
    return 0, "Current: %.2f%%" % value, [("fan_perc", value)]


def parse_apc_inrow_fanspeed(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_inrow_fanspeed"] = LegacyCheckDefinition(
    parse_function=parse_apc_inrow_fanspeed,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["16"],
    ),
    service_name="Fanspeed",
    discovery_function=inventory_apc_inrow_fanspeed,
    check_function=check_apc_inrow_fanspeed,
)
