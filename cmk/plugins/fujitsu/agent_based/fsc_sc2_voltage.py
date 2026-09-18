#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState

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

type Section = Mapping[str, ElPhase]


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

    parsed: dict[str, ElPhase] = {}
    for designation, dev_state, r_value, r_min_value, r_max_value in string_table:
        if dev_state == "2":
            continue
        try:
            value = float(r_value) / 1000.0
            min_value = float(r_min_value) / 1000.0
            max_value = float(r_max_value) / 1000.0
        except ValueError:
            parsed.setdefault(
                designation, ElPhase(device_state=(State.UNKNOWN, "Could not get all values"))
            )
            continue

        reading_state = None
        if value < min_value:
            reading_state = ReadingState(
                state=State.CRIT, text=f"too low, deceeds {min_value:.2f} V"
            )
        elif value >= max_value:
            reading_state = ReadingState(
                state=State.CRIT, text=f"too high, exceeds {max_value:.2f} V"
            )
        parsed.setdefault(
            designation, ElPhase(voltage=ReadingWithState(value=value, state=reading_state))
        )
    return parsed


def discover_fsc_sc2_voltage(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_fsc_sc2_voltage(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_fsc_sc2_voltage = SimpleSNMPSection(
    name="fsc_sc2_voltage",
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.3.1",
        oids=["3", "4", "5", "7", "8"],
    ),
    parse_function=parse_fsc_sc2_voltage,
)


check_plugin_fsc_sc2_voltage = CheckPlugin(
    name="fsc_sc2_voltage",
    service_name="Voltage %s",
    discovery_function=discover_fsc_sc2_voltage,
    check_function=check_fsc_sc2_voltage,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
