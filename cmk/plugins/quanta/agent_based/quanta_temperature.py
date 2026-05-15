#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.quanta.lib import DETECT_QUANTA, Item, parse_quanta

# .1.3.6.1.4.1.7244.1.2.1.3.4.1.1.1 1
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.1.2 2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.2.1 3
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.2.2 2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.3.1 "54 65 6D 70 5F 50 43 49 31 5F 4F 75 74 6C 65 74 01 "
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.3.2 Temp_CPU0_Inlet
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.4.1 41
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.4.2 37
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.6.1 85
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.6.2 75
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.7.1 80
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.7.2 70
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.8.1 -99
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.8.2 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.9.25 -99
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.9.26 5


Section = Mapping[str, Item]


def discover_quanta_temperature(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_quanta_temperature(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not (entry := section.get(item)):
        return

    if entry.value in (-99, None):
        yield Result(state=entry.status[0], summary=f"Status: {entry.status[1]}")
        return

    assert entry.value is not None
    yield from check_temperature(
        reading=entry.value,
        params=params,
        unique_name=f"quanta_temperature_{entry.name}",
        value_store=get_value_store(),
        dev_levels=_levels(entry.upper_levels),
        dev_levels_lower=_levels(entry.lower_levels),
        dev_status=int(entry.status[0]),
        dev_status_name=entry.status[1],
    )


def _levels(levels: tuple[float | None, float | None]) -> tuple[float, float] | None:
    warn, crit = levels
    if warn is None or crit is None:
        return None
    return warn, crit


snmp_section_quanta_temperature = SNMPSection(
    name="quanta_temperature",
    detect=DETECT_QUANTA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7244.1.2.1.3.4.1",
            oids=["1", "2", "3", "4", "6", "7", "8", "9"],
        )
    ],
    parse_function=parse_quanta,
)


check_plugin_quanta_temperature = CheckPlugin(
    name="quanta_temperature",
    service_name="Temperature %s",
    discovery_function=discover_quanta_temperature,
    check_function=check_quanta_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
