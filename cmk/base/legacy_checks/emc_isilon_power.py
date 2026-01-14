#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.emc.lib import DETECT_ISILON

check_info = {}


# Power Supply 1 Input Voltage --> Power Supply 1 Input
# Battery 1 Voltage (now) --> Battery 1 (now)
# Voltage 1.5v --> 1.5v
def isilon_power_item_name(sensor_name):
    return sensor_name.replace("Voltage", "").replace("  ", " ").strip()


def discover_emc_isilon_power(info):
    for line in info:
        # only monitor power supply currently
        if "Power Supply" in line[0] or "PS" in line[0]:
            yield isilon_power_item_name(line[0]), {}


def check_emc_isilon_power(item, params, info):
    for line in info:
        if item == isilon_power_item_name(line[0]):
            volt = float(line[1])

            infotext = "%.1f V" % volt
            warn_lower, crit_lower = params["levels_lower"]
            levelstext = f" (warn/crit below {warn_lower:.1f}/{crit_lower:.1f} V)"

            if volt < crit_lower:
                state = 2
                infotext += levelstext
            elif volt < warn_lower:
                state = 1
                infotext += levelstext
            else:
                state = 0

            return state, infotext
    return None


def parse_emc_isilon_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_isilon_power"] = LegacyCheckDefinition(
    name="emc_isilon_power",
    parse_function=parse_emc_isilon_power,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.55.1",
        oids=["3", "4"],
    ),
    service_name="Voltage %s",
    discovery_function=discover_emc_isilon_power,
    check_function=check_emc_isilon_power,
    check_ruleset_name="evolt",
    check_default_parameters={
        # the check handles only power supply input voltage currently, but there
        # are sensors for 1.0V, 1.5V, 3.3V, 12V, ... outputs.
        "levels_lower": (0.5, 0.0),
    },
)
