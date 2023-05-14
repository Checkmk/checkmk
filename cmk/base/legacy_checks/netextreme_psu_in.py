#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.netextreme import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.27.1.9.1 52550 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.9.2 43700 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.2
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.1 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.2 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.2

# Just an assumption
factory_settings["netextreme_psu_in_default_levels"] = {
    "power": (110, 120),  # This levels a recomended by the manufactorer
}


def parse_netextreme_psu_in(info):
    parsed = {}
    for psu_index, psu_usage_str, psu_factor_str in info:
        power = float(psu_usage_str) * pow(10, int(psu_factor_str))
        if power > 0:
            parsed["Input %s" % psu_index] = {
                "power": power,
            }
    return parsed


check_info["netextreme_psu_in"] = LegacyCheckDefinition(
    detect=DETECT_NETEXTREME,
    parse_function=parse_netextreme_psu_in,
    discovery_function=discover(),
    check_function=check_elphase,
    service_name="Power Supply %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.27.1",
        oids=[OIDEnd(), "9", "11"],
    ),
    check_ruleset_name="el_inphase",
    default_levels_variable="netextreme_psu_in_default_levels",
)
