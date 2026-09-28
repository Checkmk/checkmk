#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.lib.temperature import check_temperature, TempParamDict
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.8.0 31 --> EXTREME-SYSTEM-MIB::extremeCurrentTemperature.0

# Just an assumption


def discover_netextreme_temp(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service(item="System")


def check_netextreme_temp(
    item: str,  # noqa: ARG001
    params: TempParamDict,
    section: StringTable,
) -> CheckResult:
    yield from check_temperature(
        float(section[0][0]),
        params,
        unique_name="netextreme_temp_System",
        value_store=get_value_store(),
    )


def parse_netextreme_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_netextreme_temp = SimpleSNMPSection(
    name="netextreme_temp",
    parse_function=parse_netextreme_temp,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1",
        oids=["8"],
    ),
)


check_plugin_netextreme_temp = CheckPlugin(
    name="netextreme_temp",
    service_name="Temperature %s",
    discovery_function=discover_netextreme_temp,
    check_function=check_netextreme_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
