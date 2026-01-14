#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_ipr400_in_voltage(info):
    if len(info) > 0:
        yield "1", {}


def check_ipr400_in_voltage(item, params, info):
    warn, crit = params["levels_lower"]
    power = int(info[0][0]) / 1000.0  # appears to be in mV
    perfdata = [("in_voltage", power, warn, crit)]
    infotext = "in voltage: %.1fV" % power
    limitstext = "(warn/crit below %dV/%dV)" % (warn, crit)

    if power <= crit:
        return 2, infotext + ", " + limitstext, perfdata
    if power <= warn:
        return 1, infotext + ", " + limitstext, perfdata
    return 0, infotext, perfdata


def parse_ipr400_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["ipr400_in_voltage"] = LegacyCheckDefinition(
    name="ipr400_in_voltage",
    parse_function=parse_ipr400_in_voltage,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "ipr voip device ipr400"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27053.1.4.5.10",
        oids=["0"],
    ),
    service_name="IN Voltage %s",
    discovery_function=discover_ipr400_in_voltage,
    check_function=check_ipr400_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        # 11.5-13.8V is the operational voltage according
        # to the manual
        "levels_lower": (12.0, 11.0),
    },
)
