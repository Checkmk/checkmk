#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.cisco_ucs import DETECT
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-30

# .1.3.6.1.4.1.9.9.719.1.9.44.1.4  cucsComputeRackUnitMbTempStatsAmbientTemp
# .1.3.6.1.4.1.9.9.719.1.9.44.1.8  cucsComputeRackUnitMbTempStatsFrontTemp
# .1.3.6.1.4.1.9.9.719.1.9.44.1.13 cucsComputeRackUnitMbTempStatsIoh1Temp
# .1.3.6.1.4.1.9.9.719.1.9.44.1.21 cucsComputeRackUnitMbTempStatsRearTemp


def parse_cisco_ucs_temp_env(string_table):
    return (
        {
            "Ambient": string_table[0][0],
            "Front": string_table[0][1],
            "IO-Hub": string_table[0][2],
            "Rear": string_table[0][3],
        }
        if string_table
        else None
    )


def discover_cisco_ucs_temp_env(info):
    for name, _temp in info.items():
        yield name, {}


def check_cisco_ucs_temp_env(item, params, info):
    for name, temp in info.items():
        if item == name:
            yield check_temperature(int(temp), params, "cisco_ucs_temp_env_%s" % name)


check_info["cisco_ucs_temp_env"] = LegacyCheckDefinition(
    name="cisco_ucs_temp_env",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.9.44.1",
        oids=["4", "8", "13", "21"],
    ),
    parse_function=parse_cisco_ucs_temp_env,
    service_name="Temperature %s",
    discovery_function=discover_cisco_ucs_temp_env,
    check_function=check_cisco_ucs_temp_env,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
