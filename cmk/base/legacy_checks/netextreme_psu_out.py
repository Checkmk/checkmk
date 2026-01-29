#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyDiscoveryResult
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

check_info = {}

# .1.3.6.1.4.1.1916.1.1.1.38.1.3.1.1 11960 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputVoltage.1.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.3.1.2 0 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputVoltage.1.2
# .1.3.6.1.4.1.1916.1.1.1.38.1.3.2.1 11990 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputVoltage.2.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.3.2.2 0 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputVoltage.2.2
# .1.3.6.1.4.1.1916.1.1.1.38.1.4.1.1 2900 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputCurrent.1.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.4.1.2 0 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputCurrent.1.2
# .1.3.6.1.4.1.1916.1.1.1.38.1.4.2.1 2260 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputCurrent.2.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.4.2.2 0 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputCurrent.2.2
# .1.3.6.1.4.1.1916.1.1.1.38.1.5.1.1 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputUnitMultiplier.1.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.5.1.2 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputUnitMultiplier.1.2
# .1.3.6.1.4.1.1916.1.1.1.38.1.5.2.1 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputUnitMultiplier.2.1
# .1.3.6.1.4.1.1916.1.1.1.38.1.5.2.2 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyOutputUnitMultiplier.2.2

# Just assumed


def parse_netextreme_psu_out(string_table: StringTable) -> Mapping[str, Mapping[str, float]]:
    parsed: dict[str, dict[str, float]] = {}
    for psu_index, psu_voltage_str, psu_current_str, psu_factor_str in string_table:
        psu_name = "Output %s" % psu_index
        psu_voltage = float(psu_voltage_str) * pow(10, int(psu_factor_str))
        psu_current = float(psu_current_str) * pow(10, int(psu_factor_str))
        # 0 in this field tells the psu doesnt support output voltage/current reading
        # or output voltage/current read error
        if float(psu_voltage_str) > 0 and float(psu_current_str) > 0:
            parsed[psu_name] = {
                "voltage": psu_voltage,
                "current": psu_current,
            }
        elif float(psu_voltage_str) > 0 and float(psu_current_str) == 0:
            parsed[psu_name] = {
                "voltage": psu_voltage,
            }
        elif float(psu_voltage_str) == 0 and float(psu_current_str) > 0:
            parsed[psu_name] = {
                "current": psu_current,
            }

    return parsed


def discover_netextreme_psu_out(
    section: Mapping[str, Mapping[str, float]],
) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


check_info["netextreme_psu_out"] = LegacyCheckDefinition(
    name="netextreme_psu_out",
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.38.1",
        oids=[OIDEnd(), "3", "4", "5"],
    ),
    parse_function=parse_netextreme_psu_out,
    service_name="Power Supply %s",
    discovery_function=discover_netextreme_psu_out,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "voltage": (11, 10),
        "current": (4, 5),
    },
)
