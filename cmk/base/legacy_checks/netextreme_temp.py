#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

check_info = {}

# .1.3.6.1.4.1.1916.1.1.1.8.0 31 --> EXTREME-SYSTEM-MIB::extremeCurrentTemperature.0

# Just an assumption


def discover_netextreme_temp(info):
    return [("System", {})]


def check_netextreme_temp(item, params, info):
    return check_temperature(float(info[0][0]), params, "netextreme_temp_System")


def parse_netextreme_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["netextreme_temp"] = LegacyCheckDefinition(
    name="netextreme_temp",
    parse_function=parse_netextreme_temp,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1",
        oids=["8"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_netextreme_temp,
    check_function=check_netextreme_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
