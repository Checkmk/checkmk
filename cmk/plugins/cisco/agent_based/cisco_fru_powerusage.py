#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.cisco.lib import DETECT_CISCO
from cmk.plugins.lib.elphase import check_elphase, ElPhase

# .1.3.6.1.4.1.9.9.117.1.1.1.1.2.16  "centiAmpsAt12V"
#  some more examples (but we dont know all):
#       milliAmps12v
#       centiAmpsAt12V
#       Amps @ 12V
#       CentiAmps @ 12V
#       Amps @ 50
#   => calculate power = factor * amps * volt

# .1.3.6.1.4.1.9.9.117.1.1.4.1.1.16 11333
# .1.3.6.1.4.1.9.9.117.1.1.4.1.2.16 9666
# .1.3.6.1.4.1.9.9.117.1.1.4.1.3.16 6000
# .1.3.6.1.4.1.9.9.117.1.1.4.1.4.16 122

# .1.3.6.1.4.1.9.9.117.1.1.4.1.1.13 11333
# .1.3.6.1.4.1.9.9.117.1.1.4.1.2.13 5583
# .1.3.6.1.4.1.9.9.117.1.1.4.1.3.13 6980
# .1.3.6.1.4.1.9.9.117.1.1.4.1.4.13 0       <= exclude


def parse_cisco_fru_powerusage(
    string_table: Sequence[StringTable],
) -> dict[str, dict[str, float]]:
    parsed: dict[str, dict[str, float]] = {}
    powerunit, powervals = string_table
    if powerunit and powervals:
        oidend, powerunit_str = powerunit[0]
        factor_str, voltage_str = powerunit_str.lower().split("amps")

        if "milli" in factor_str.lower():
            factor = 0.001
        elif "centi" in factor_str.lower():
            factor = 0.01
        else:
            factor = 1.0

        voltage = float(
            voltage_str.lower().replace("at", "").replace("@", "").replace("v", "").strip()
        )

        if oidend == powervals[0][0]:
            system_total, system_drawn, inline_total, inline_drawn = map(float, powervals[0][1:])
            for what, val in [
                ("system total", system_total),  # Gesamtstrom
                ("system drawn", system_drawn),  # aufgenommene Gesamtstromstaerke
                ("inline total", inline_total),
                ("inline drawn", inline_drawn),
            ]:
                parsed.setdefault(
                    what,
                    {
                        "power": factor * val * voltage,
                        "current": factor * val,
                        "voltage": voltage,
                    },
                )

    return parsed


def discover_cisco_fru_powerusage(section: dict[str, dict[str, float]]) -> DiscoveryResult:
    for what, data in section.items():
        if data["current"] > 0:
            yield Service(item=what)


def check_cisco_fru_powerusage(
    item: str, params: Mapping[str, Any], section: dict[str, dict[str, float]]
) -> CheckResult:
    if item not in section:
        return
    yield from check_elphase(params, ElPhase.from_dict(section[item]))


snmp_section_cisco_fru_powerusage = SNMPSection(
    name="cisco_fru_powerusage",
    detect=DETECT_CISCO,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.117.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.117.1.1.4.1",
            oids=[OIDEnd(), "1", "2", "3", "4"],
        ),
    ],
    parse_function=parse_cisco_fru_powerusage,
)


check_plugin_cisco_fru_powerusage = CheckPlugin(
    name="cisco_fru_powerusage",
    service_name="FRU power usage %s",
    discovery_function=discover_cisco_fru_powerusage,
    check_function=check_cisco_fru_powerusage,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
