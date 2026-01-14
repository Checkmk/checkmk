#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

check_info = {}

# .1.3.6.1.4.1.1916.1.32.1.2.0 59 --> EXTREME-SOFTWARE-MONITOR-MIB::extremeCpuMonitorTotalUtilization.0$

# As in some other checks


def discover_netextreme_cpu_util(info):
    if info:
        yield None, {}


def check_netextreme_cpu_util(_no_item, params, info):
    return check_cpu_util(float(info[0][0]), params)


def parse_netextreme_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


check_info["netextreme_cpu_util"] = LegacyCheckDefinition(
    name="netextreme_cpu_util",
    parse_function=parse_netextreme_cpu_util,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.32.1.2",
        oids=["0"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_netextreme_cpu_util,
    check_function=check_netextreme_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
