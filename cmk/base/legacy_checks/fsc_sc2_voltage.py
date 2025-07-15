#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}

# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.1 "BATT 3.0V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.2 "STBY 12V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.3 "STBY 5V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.4 "STBY 3.3V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.5 "LAN 1.8V STBY"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.6 "iRMC 1.5V STBY"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.7 "LAN 1.0V STBY"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.8 "MAIN 12V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.3.1.9 "MAIN 5V"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.2 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.3 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.4 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.5 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.6 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.7 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.8 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.4.1.9 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.1 3270
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.2 11880
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.3 5100
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.4 3350
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.5 1800
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.6 1460
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.7 980
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.8 12160
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.5.1.9 4980
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.1 2010
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.2 11280
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.3 4630
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.4 3020
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.5 1670
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.6 1390
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.7 930
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.8 11310
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.7.1.9 4630
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.1 3500
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.2 12960
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.3 5420
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.4 3570
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.5 1930
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.6 1610
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.7 1080
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.8 12900
# .1.3.6.1.4.1.231.2.10.2.2.10.6.3.1.8.1.9 5420

Section = Mapping[str, Mapping[str, float | tuple[int, str] | tuple[float, tuple[int, str]]]]


def parse_fsc_sc2_voltage(string_table: StringTable) -> Section:
    # dev_state:
    # sc2VoltageStatus OBJECT-TYPE
    # SYNTAX       INTEGER
    # {
    #     unknown(1),
    #     not-available(2),
    #     ok(3),
    #     too-low(4),
    #     too-high(5),
    #     sensor-failed(6)
    # }
    # ACCESS       read-only
    # STATUS       mandatory
    # DESCRIPTION  "Voltage status"
    # ::= { sc2Voltages 4 }

    parsed: dict[str, dict[str, float | tuple[int, str] | tuple[float, tuple[int, str]]]] = {}
    for designation, dev_state, r_value, r_min_value, r_max_value in string_table:
        if dev_state == "2":
            continue
        try:
            value = float(r_value) / 1000.0
            min_value = float(r_min_value) / 1000.0
            max_value = float(r_max_value) / 1000.0
        except ValueError:
            parsed.setdefault(designation, {"device_state": (3, "Could not get all values")})
            continue

        state_info: float | tuple[float, tuple[int, str]] = value
        if value < min_value:
            state_info = value, (2, "too low, deceeds %.2f V" % min_value)
        elif value >= max_value:
            state_info = value, (2, "too high, exceeds %.2f V" % max_value)
        parsed.setdefault(designation, {"voltage": state_info})
    return parsed


def discover_fsc_sc2_voltage(section):
    yield from ((item, {}) for item in section)


check_info["fsc_sc2_voltage"] = LegacyCheckDefinition(
    name="fsc_sc2_voltage",
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.3.1",
        oids=["3", "4", "5", "7", "8"],
    ),
    parse_function=parse_fsc_sc2_voltage,
    service_name="Voltage %s",
    discovery_function=discover_fsc_sc2_voltage,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
