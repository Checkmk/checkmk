#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_processors(info):
    return [(x[0], None) for x in info if x[1] != "4" and x[0] != ""]


def check_dell_om_processors(item, _no_params, info):
    # Probetypes found in check_openmanage3.pl
    cpu_states = {
        "1": "Other",  # other than following values
        "2": "Unknown",  # unknown
        "3": "Enabled",  # enabled
        "4": "User Disabled",  # disabled by user via BIOS setup
        "5": "BIOS Disabled",  # disabled by BIOS (POST error)
        "6": "Idle",  # idle
    }

    cpu_readings = {
        "0": "Unknown",
        "1": "Internal Error",  # Internal Error
        "2": "Thermal Trip",  # Thermal Trip
        "32": "Configuration Error",  # Configuration Error
        "128": "Present",  # Processor Present
        "256": "Disabled",  # Processor Disabled
        "512": "Terminator Present",  # Terminator Present
        "1024": "Throttled",  # Processor Throttled
    }

    for index, status, manuf, status2, reading in info:
        if index == item:
            state = 0
            if not status:
                status = status2

            if status != "3":
                state = 2
            if reading in ["1", "32"]:
                state = 2

            if status in cpu_states:
                cpu_state_readable = cpu_states[status]
            else:
                cpu_state_readable = "unknown[%s]" % status
                state = 3

            if reading in cpu_readings:
                cpu_reading_readable = cpu_readings[reading]
            else:
                cpu_reading_readable = "unknown[%s]" % reading
                state = 3
            return state, "[{}] CPU status: {}, CPU reading: {}".format(
                manuf,
                cpu_state_readable,
                cpu_reading_readable,
            )

    return 2, "Processor not found"


def parse_dell_om_processors(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_processors"] = LegacyCheckDefinition(
    parse_function=parse_dell_om_processors,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.1100",
        oids=["30.1.2", "30.1.5", "30.1.8", "30.1.9", "32.1.6"],
    ),
    service_name="Processor %s",
    discovery_function=inventory_dell_om_processors,
    check_function=check_dell_om_processors,
)
