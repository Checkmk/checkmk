#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.32.1.2.0 59 --> EXTREME-SOFTWARE-MONITOR-MIB::extremeCpuMonitorTotalUtilization.0$

# As in some other checks


def discover_netextreme_cpu_util(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_netextreme_cpu_util(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    yield from check_cpu_util(
        util=float(section[0][0]),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_netextreme_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netextreme_cpu_util = SimpleSNMPSection(
    name="netextreme_cpu_util",
    parse_function=parse_netextreme_cpu_util,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.32.1.2",
        oids=["0"],
    ),
)


check_plugin_netextreme_cpu_util = CheckPlugin(
    name="netextreme_cpu_util",
    service_name="CPU utilization",
    discovery_function=discover_netextreme_cpu_util,
    check_function=check_netextreme_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
