#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

type Section = Mapping[str, ElPhase]

# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.3.1 "CPU1 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.3.2 "CPU2 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.4.1 "HDD Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.7.1 "System Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.10.1 "PSU1 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.10.2 "PSU2 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.224.1 "Total Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.224.2 "Total Power Out"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.3.1 5
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.3.2 0
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.4.1 8
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.7.1 50
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.10.1 52
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.10.2 40
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.224.1 92
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.224.2 68


def parse_fsc_sc2_power_consumption(string_table: StringTable) -> Section:
    parsed: dict[str, ElPhase] = {}
    for designation, value in string_table:
        # sometimes the device does not return a value
        if not value:
            parsed.setdefault(
                designation,
                ElPhase(device_state=(State.UNKNOWN, "Error on device while reading value")),
            )
        else:
            parsed.setdefault(designation, ElPhase(power=ReadingWithState(value=int(value))))
    return parsed


def discover_fsc_sc2_power_consumption(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_fsc_sc2_power_consumption(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_fsc_sc2_power_consumption = SimpleSNMPSection(
    name="fsc_sc2_power_consumption",
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.7.1",
        oids=["4", "5"],
    ),
    parse_function=parse_fsc_sc2_power_consumption,
)


check_plugin_fsc_sc2_power_consumption = CheckPlugin(
    name="fsc_sc2_power_consumption",
    service_name="Power Comsumption %s",
    discovery_function=discover_fsc_sc2_power_consumption,
    check_function=check_fsc_sc2_power_consumption,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
