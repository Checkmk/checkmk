#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.netextreme import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.8.0 31 --> EXTREME-SYSTEM-MIB::extremeCurrentTemperature.0

# Just an assumption


def inventory_netextreme_temp(info):
    return [("System", {})]


def check_netextreme_temp(item, params, info):
    return check_temperature(float(info[0][0]), params, "netextreme_temp_System")


check_info["netextreme_temp"] = LegacyCheckDefinition(
    detect=DETECT_NETEXTREME,
    discovery_function=inventory_netextreme_temp,
    check_function=check_netextreme_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1",
        oids=["8"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
