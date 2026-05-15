#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
)
from cmk.plugins.quanta.lib import DETECT_QUANTA, Item, parse_quanta

# .1.3.6.1.4.1.7244.1.2.1.3.5.1.1.14 14
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.1.15 15
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.2.14 3
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.2.15 3
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.3.14 Volt_VR_DIMM_GH
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.3.15 "56 6F 6C 74 5F 53 41 53 5F 45 58 50 5F 30 56 39 01 "
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.4.14 1220
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.4.15 923
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.6.14 1319
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.6.15 988
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.7.14 -99
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.7.15 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.8.14 -99
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.8.15 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.9.14 1079
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.9.15 806


Section = Mapping[str, Item]


def _levels(levels: tuple[float | None, float | None]) -> tuple[float, float] | None:
    warn, crit = levels
    if warn is None or crit is None:
        return None
    return warn, crit


def discover_quanta_voltage(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_quanta_voltage(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (entry := section.get(item)):
        return
    yield Result(state=entry.status[0], summary=f"Status: {entry.status[1]}")

    if entry.value in (-99, None):
        return

    assert entry.value is not None
    yield from check_levels_v1(
        entry.value,
        metric_name="voltage",
        levels_upper=params.get("levels", _levels(entry.upper_levels)),
        levels_lower=params.get("levels_lower", _levels(entry.lower_levels)),
        render_func=lambda x: f"{x:.2f} V",
    )


snmp_section_quanta_voltage = SNMPSection(
    name="quanta_voltage",
    detect=DETECT_QUANTA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7244.1.2.1.3.5.1",
            oids=["1", "2", "3", "4", "6", "7", "8", "9"],
        )
    ],
    parse_function=parse_quanta,
)


check_plugin_quanta_voltage = CheckPlugin(
    name="quanta_voltage",
    service_name="Voltage %s",
    discovery_function=discover_quanta_voltage,
    check_function=check_quanta_voltage,
    check_ruleset_name="voltage",
    check_default_parameters={},
)
