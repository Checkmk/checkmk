#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.netextreme import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.32.1.2.0 59 --> EXTREME-SOFTWARE-MONITOR-MIB::extremeCpuMonitorTotalUtilization.0$

# As in some other checks


def inventory_netextreme_cpu_util(info):
    if info:
        yield None, {}


def check_netextreme_cpu_util(_no_item, params, info):
    return check_cpu_util(float(info[0][0]), params)


check_info["netextreme_cpu_util"] = LegacyCheckDefinition(
    detect=DETECT_NETEXTREME,
    discovery_function=inventory_netextreme_cpu_util,
    check_function=check_netextreme_cpu_util,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.32.1.2",
        oids=["0"],
    ),
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
