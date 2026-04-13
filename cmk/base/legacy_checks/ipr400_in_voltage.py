#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def inventory_ipr400_in_voltage(info):
    if len(info) > 0:
        yield "1", {}


def check_ipr400_in_voltage(item, params, info):
    warn_lower, crit_lower = params["levels_lower"]
    warn_upper, crit_upper = params.get("levels_upper", (None, None))
    power = int(info[0][0]) / 1000.0  # appears to be in mV
    perfdata = [
        (
            "in_voltage",
            power,
            warn_upper if warn_upper is not None else warn_lower,
            crit_upper if crit_upper is not None else crit_lower,
        )
    ]
    infotext = "in voltage: %.1fV" % power
    lower_text = f"(warn/crit below {warn_lower}V/{crit_lower}V)"
    upper_text = f"(warn/crit at or above {warn_upper}V/{crit_upper}V)"

    if power <= crit_lower:
        return 2, infotext + ", " + lower_text, perfdata
    if crit_upper is not None and power >= crit_upper:
        return 2, infotext + ", " + upper_text, perfdata
    if power <= warn_lower:
        return 1, infotext + ", " + lower_text, perfdata
    if warn_upper is not None and power >= warn_upper:
        return 1, infotext + ", " + upper_text, perfdata
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
    discovery_function=inventory_ipr400_in_voltage,
    check_function=check_ipr400_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        # 11.5-13.8V is the operational voltage according
        # to the manual
        "levels_lower": (12.0, 11.0),
    },
)
