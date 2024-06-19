#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_OPENMANAGE

# example output
# .1.3.6.1.4.1.674.10892.1.600.10.1.2.1.1 1
# .1.3.6.1.4.1.674.10892.1.600.10.1.5.1.1 3
# .1.3.6.1.4.1.674.10892.1.600.10.1.6.1.1 0
# .1.3.6.1.4.1.674.10892.1.600.12.1.2.1.1 1
# .1.3.6.1.4.1.674.10892.1.600.12.1.2.1.2 2
# .1.3.6.1.4.1.674.10892.1.600.12.1.5.1.1 3
# .1.3.6.1.4.1.674.10892.1.600.12.1.5.1.2 3
# .1.3.6.1.4.1.674.10892.1.600.12.1.7.1.1 9
# .1.3.6.1.4.1.674.10892.1.600.12.1.7.1.2 9
# .1.3.6.1.4.1.674.10892.1.600.12.1.8.1.1 PS1 Status
# .1.3.6.1.4.1.674.10892.1.600.12.1.8.1.2 PS2 Status


def inventory_dell_om_power(info):
    for index, _status, _count in info[0]:
        yield (index, None)


def check_dell_om_power(item, params, info):
    translate_status = {
        "1": (3, "other"),
        "2": (3, "unknown"),
        "3": (0, "full"),
        "4": (1, "degraded"),
        "5": (2, "lost"),
        "6": (0, "not redundant"),
        "7": (1, "redundancy offline"),
    }

    for index, status, _count in info[0]:
        if index == item:
            state, state_readable = translate_status[status]
            yield state, "Redundancy status: %s" % state_readable


def parse_dell_om_power(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["dell_om_power"] = LegacyCheckDefinition(
    parse_function=parse_dell_om_power,
    detect=DETECT_OPENMANAGE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.1.600.10.1",
            oids=["2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.1.600.12.1",
            oids=["2", "5", "7", "8"],
        ),
    ],
    service_name="Power Supply Redundancy %s",
    discovery_function=inventory_dell_om_power,
    check_function=check_dell_om_power,
)


def inventory_dell_om_power_unit(info):
    for line in info[1]:
        yield (line[0], None)


def check_dell_om_power_unit(item, _no_params, info):
    translate_status = {
        "1": (3, "OTHER"),
        "2": (3, "UNKNOWN"),
        "3": (0, "OK"),
        "4": (1, "NONCRITICAL"),
        "5": (2, "CRITICAL"),
        "6": (2, "NONRECOVERABLE"),
    }

    translate_type = {
        "1": "OTHER",
        "2": "UNKNOWN",
        "3": "LINEAR",
        "4": "SWITCHING",
        "5": "BATTERY",
        "6": "UPS",
        "7": "CONVERTER",
        "8": "REGULATOR",
        "9": "AC",
        "10": "DC",
        "11": "VRM",
    }

    for index, status, psu_type, location in info[1]:
        if index == item:
            state, state_readable = translate_status[status]
            psu_type_readable = translate_type[psu_type]
            yield state, "Status: {}, Type: {}, Name: {}".format(
                state_readable,
                psu_type_readable,
                location,
            )


check_info["dell_om_power.unit"] = LegacyCheckDefinition(
    service_name="Power Supply %s",
    sections=["dell_om_power"],
    discovery_function=inventory_dell_om_power_unit,
    check_function=check_dell_om_power_unit,
)
