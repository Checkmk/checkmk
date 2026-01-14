#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# upsBatteryStatus              1.3.6.1.4.1.4555.1.1.1.1.2.1
# upsSecondsOnBattery           1.3.6.1.4.1.4555.1.1.1.1.2.2
# upsEstimatedMinutesRemaining  1.3.6.1.4.1.4555.1.1.1.1.2.3
# upsEstimatedChargeRemaining   1.3.6.1.4.1.4555.1.1.1.1.2.4
# upsBatteryVoltage             1.3.6.1.4.1.4555.1.1.1.1.2.5
# upsBatteryTemperature         1.3.6.1.4.1.4555.1.1.1.1.2.6

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.ups_socomec.lib import DETECT_SOCOMEC

check_info = {}


def discover_ups_socomec_capacity(info):
    if len(info) > 0:
        return [(None, {})]
    return []


def check_ups_socomec_capacity(item, params, info):
    # To support inventories with the old version
    # TODO This needs to be reworked. Defaults should not be coded into a check in such a fashion.
    if isinstance(params, tuple):  # old format with 2 params in tuple
        warn, crit = params
        cap_warn, cap_crit = (95, 90)
    elif isinstance(params, dict):  # new dict format
        warn, crit = params.get("battime", (0, 0))
        cap_warn, cap_crit = params.get("capacity", (95, 90))
    else:
        warn, crit = (0, 0)
        cap_warn, cap_crit = (95, 90)

    time_on_bat, minutes_left, percent_fuel = map(int, info[0])

    # Check time left on battery
    if minutes_left != -1:
        levelsinfo = ""
        if minutes_left <= crit:
            state = 2
            levelsinfo = " (crit at %d min)" % cap_crit
        elif minutes_left < warn:
            state = 1
            levelsinfo = " (warn at %d min)" % cap_warn
        else:
            state = 0
        yield (
            state,
            "%d min left on battery" % minutes_left + levelsinfo,
            [("capacity", minutes_left, warn, crit)],
        )

    # Check percentual capacity
    levelsinfo = ""
    if percent_fuel <= cap_crit:
        state = 2
        levelsinfo = " (crit at %d%%)" % cap_crit
    elif percent_fuel < cap_warn:
        state = 1
        levelsinfo = " (warn at %d%%)" % cap_warn
    else:
        state = 0
    yield (
        state,
        "capacity: %d%%" % percent_fuel + levelsinfo,
        [("percent", percent_fuel, cap_warn, cap_crit)],
    )

    # Output time on battery
    if time_on_bat > 0:
        yield 0, "On battery for %d min" % time_on_bat


def parse_ups_socomec_capacity(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_socomec_capacity"] = LegacyCheckDefinition(
    name="ups_socomec_capacity",
    parse_function=parse_ups_socomec_capacity,
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.2",
        oids=["2", "3", "4"],
    ),
    service_name="Battery capacity",
    discovery_function=discover_ups_socomec_capacity,
    check_function=check_ups_socomec_capacity,
    check_ruleset_name="ups_capacity",
    check_default_parameters={"battime": (0, 0), "capacity": (95, 90)},
)
