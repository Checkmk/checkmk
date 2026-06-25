#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# upsBatteryStatus              1.3.6.1.4.1.4555.1.1.1.1.2.1
# upsSecondsOnBattery           1.3.6.1.4.1.4555.1.1.1.1.2.2
# upsEstimatedMinutesRemaining  1.3.6.1.4.1.4555.1.1.1.1.2.3
# upsEstimatedChargeRemaining   1.3.6.1.4.1.4555.1.1.1.1.2.4
# upsBatteryVoltage             1.3.6.1.4.1.4555.1.1.1.1.2.5
# upsBatteryTemperature         1.3.6.1.4.1.4555.1.1.1.1.2.6


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.ups.lib_socomec import DETECT_SOCOMEC


def parse_ups_socomec_capacity(string_table: StringTable) -> StringTable:
    return string_table


def discover_ups_socomec_capacity(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_ups_socomec_capacity(params: object, section: StringTable) -> CheckResult:
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

    time_on_bat, minutes_left, percent_fuel = map(int, section[0])

    # Check time left on battery
    if minutes_left != -1:
        levelsinfo = ""
        if minutes_left <= crit:
            state = State.CRIT
            levelsinfo = " (crit at %d min)" % cap_crit
        elif minutes_left < warn:
            state = State.WARN
            levelsinfo = " (warn at %d min)" % cap_warn
        else:
            state = State.OK
        warn_float: float | None = float(warn) if warn else None
        crit_float: float | None = float(crit) if crit else None
        yield Result(state=state, summary="%d min left on battery" % minutes_left + levelsinfo)
        yield Metric("capacity", float(minutes_left), levels=(warn_float, crit_float))

    # Check percentual capacity
    levelsinfo = ""
    if percent_fuel <= cap_crit:
        state = State.CRIT
        levelsinfo = " (crit at %d%%)" % cap_crit
    elif percent_fuel < cap_warn:
        state = State.WARN
        levelsinfo = " (warn at %d%%)" % cap_warn
    else:
        state = State.OK
    cap_warn_float: float | None = float(cap_warn) if cap_warn else None
    cap_crit_float: float | None = float(cap_crit) if cap_crit else None
    yield Result(state=state, summary="capacity: %d%%" % percent_fuel + levelsinfo)
    yield Metric("percent", float(percent_fuel), levels=(cap_warn_float, cap_crit_float))

    # Output time on battery
    if time_on_bat > 0:
        yield Result(state=State.OK, summary="On battery for %d min" % time_on_bat)


snmp_section_ups_socomec_capacity = SimpleSNMPSection(
    name="ups_socomec_capacity",
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.2",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_ups_socomec_capacity,
)


check_plugin_ups_socomec_capacity = CheckPlugin(
    name="ups_socomec_capacity",
    service_name="Battery capacity",
    discovery_function=discover_ups_socomec_capacity,
    check_function=check_ups_socomec_capacity,
    check_ruleset_name="ups_capacity",
    check_default_parameters={"battime": (0, 0), "capacity": (95, 90)},
)
