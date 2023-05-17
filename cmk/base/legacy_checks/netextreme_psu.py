#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.netextreme import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.40.1.0 96250 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageValue.0
# .1.3.6.1.4.1.1916.1.1.1.40.2.0 -3 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageUnitMultiplier.0

# Maximum power consumption is 123 W
# as in the documentation 'Summit-X460-G2-DS.pdf'
factory_settings["netextreme_psu_default_levels"] = {
    "power": (110, 120),
}


def parse_netextreme_psu(info):
    try:
        return {"1": {"power": float(info[0][0]) * pow(10, int(info[0][1]))}}
    except (IndexError, ValueError):
        return {}


check_info["netextreme_psu"] = LegacyCheckDefinition(
    detect=DETECT_NETEXTREME,
    parse_function=parse_netextreme_psu,
    discovery_function=discover(),
    check_function=check_elphase,
    service_name="Power Supply %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.40",
        oids=["1", "2"],
    ),
    check_ruleset_name="el_inphase",
    default_levels_variable="netextreme_psu_default_levels",
    check_default_parameters={
        "power": (110, 120),
    },
)
