#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.lib.netextreme import DETECT_NETEXTREME

check_info = {}

# .1.3.6.1.4.1.1916.1.1.1.40.1.0 96250 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageValue.0
# .1.3.6.1.4.1.1916.1.1.1.40.2.0 -3 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageUnitMultiplier.0

# Maximum power consumption is 123 W
# as in the documentation 'Summit-X460-G2-DS.pdf'


def parse_netextreme_psu(string_table):
    try:
        return {"1": {"power": float(string_table[0][0]) * pow(10, int(string_table[0][1]))}}
    except (IndexError, ValueError):
        return {}


def discover_netextreme_psu(section):
    yield from ((item, {}) for item in section)


check_info["netextreme_psu"] = LegacyCheckDefinition(
    name="netextreme_psu",
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.40",
        oids=["1", "2"],
    ),
    parse_function=parse_netextreme_psu,
    service_name="Power Supply %s",
    discovery_function=discover_netextreme_psu,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "power": (110, 120),
    },
)
