#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
from typing import Mapping

from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL

alcatel_power_operstate_map = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "secondary",
    "6": "not present",
    "7": "unpowered",
    "9": "master",
}

alcatel_power_no_power_supply_info = "no power supply"

alcatel_power_type_map = {
    "0": alcatel_power_no_power_supply_info,
    "1": "AC",
    "2": "DC",
}

AlcatelPowerEntry = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "AlcatelPowerEntry",
    [
        "oper_state_readable",
        "power_type",
    ],
)

Section = Mapping[str, AlcatelPowerEntry]


def parse_alcatel_power(string_table: StringTable) -> Section:
    return {
        oidend: AlcatelPowerEntry(
            alcatel_power_operstate_map.get(status, "unknown[%s]" % status),
            alcatel_power_type_map.get(power_type, alcatel_power_no_power_supply_info),
        )
        for oidend, status, power_type in reversed(string_table)
    }


@discover
def inventory_alcatel_power(_oidend, device):
    return (
        device.power_type != alcatel_power_no_power_supply_info
        and device.oper_state_readable != "not present"
    )


@get_parsed_item_data
def check_alcatel_power(item, _no_params, device):
    if device.oper_state_readable == "up":
        state = 0
    else:
        state = 2
    yield state, "[%s] Operational status: %s" % (device.power_type, device.oper_state_readable)


check_info["alcatel_power"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL,
    parse_function=parse_alcatel_power,
    check_function=check_alcatel_power,
    discovery_function=inventory_alcatel_power,
    service_name="Power Supply %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.1.1.1.1",
        oids=[OIDEnd(), "2", "36"],
    ),
)
