#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def discover_ipr400_in_voltage(section: StringTable) -> DiscoveryResult:
    if len(section) > 0:
        yield Service(item="1")


def check_ipr400_in_voltage(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    warn, crit = params["levels_lower"]
    warn_upper, crit_upper = params.get("levels_upper", (None, None))
    power = int(section[0][0]) / 1000.0  # appears to be in mV
    infotext = f"in voltage: {power:.1f}V"

    if power <= crit:
        yield Result(state=State.CRIT, summary=f"{infotext}, (warn/crit below {warn}V/{crit}V)")
    elif crit_upper is not None and power >= crit_upper:
        yield Result(
            state=State.CRIT,
            summary=f"{infotext}, (warn/crit at or above {warn_upper}V/{crit_upper}V)",
        )
    elif power <= warn:
        yield Result(state=State.WARN, summary=f"{infotext}, (warn/crit below {warn}V/{crit}V)")
    elif warn_upper is not None and power >= warn_upper:
        yield Result(
            state=State.WARN,
            summary=f"{infotext}, (warn/crit at or above {warn_upper}V/{crit_upper}V)",
        )
    else:
        yield Result(state=State.OK, summary=infotext)
    yield Metric(
        "in_voltage",
        power,
        levels=(warn_upper, crit_upper) if warn_upper is not None else (warn, crit),
    )


def parse_ipr400_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ipr400_in_voltage = SimpleSNMPSection(
    name="ipr400_in_voltage",
    parse_function=parse_ipr400_in_voltage,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "ipr voip device ipr400"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27053.1.4.5.10",
        oids=["0"],
    ),
)

check_plugin_ipr400_in_voltage = CheckPlugin(
    name="ipr400_in_voltage",
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
