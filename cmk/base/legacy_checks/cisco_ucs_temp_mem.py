#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-30

# .1.3.6.1.4.1.9.9.719.1.30.12.1.2 memory Unit Name
# .1.3.6.1.4.1.9.9.719.1.30.12.1.6 cucsMemoryUnitEnvStatsTemperature


def discover_cisco_ucs_temp_mem(info):
    for name, _value in info:
        name = name.split("/")[3]
        yield name, {}


def check_cisco_ucs_temp_mem(item, params, info):
    for name, value in info:
        name = name.split("/")[3]
        if name == item:
            temp = int(value)
            return check_temperature(temp, params, "cisco_temp_%s" % item)
    return None


def parse_cisco_ucs_temp_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_ucs_temp_mem"] = LegacyCheckDefinition(
    name="cisco_ucs_temp_mem",
    parse_function=parse_cisco_ucs_temp_mem,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.30.12.1",
        oids=["2", "6"],
    ),
    service_name="Temperature Mem %s",
    discovery_function=discover_cisco_ucs_temp_mem,
    check_function=check_cisco_ucs_temp_mem,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (75.0, 85.0),
    },
)
