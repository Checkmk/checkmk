#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections

from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL_AOS7

alcatel_power_aos7_operability_to_status_mapping = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "secondary",
    "6": "not present",  # no check status required
    "7": "unpowered",
    "8": "master",
    "9": "idle",
    "10": "power save",
}

alcatel_power_aos7_no_power_supply = "no power supply"

alcatel_power_aos7_power_type_mapping = {
    "0": alcatel_power_aos7_no_power_supply,
    "1": "AC",
    "2": "DC",
}

PowerSupplyEntry = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "PowerSupplyEntry", "status_readable power_supply_type"
)


def parse_alcatel_power_aos7(info):
    return {
        item: PowerSupplyEntry(
            alcatel_power_aos7_operability_to_status_mapping[operability_status],
            alcatel_power_aos7_power_type_mapping.get(
                power_supply_type,
                alcatel_power_aos7_no_power_supply,
            ),
        )
        for (item, operability_status, power_supply_type) in info
    }


@discover
def inventory_alcatel_power_aos7(_oidend, device):
    return (
        device.power_supply_type != alcatel_power_aos7_no_power_supply
        and device.status_readable != "not present"
    )


@get_parsed_item_data
def check_alcatel_power_aos7(item, _no_params, device):
    if device.status_readable == "up":
        status = 0
    else:
        status = 2
    yield status, "[%s] Status: %s" % (device.power_supply_type, device.status_readable)


check_info["alcatel_power_aos7"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL_AOS7,
    parse_function=parse_alcatel_power_aos7,
    check_function=check_alcatel_power_aos7,
    discovery_function=inventory_alcatel_power_aos7,
    service_name="Power Supply %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.1.1.1.1.1.1",
        oids=[OIDEnd(), "2", "35"],
    ),
)
