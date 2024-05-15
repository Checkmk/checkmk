#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
)
from cmk.plugins.liebert.agent_based.lib import (
    DETECT_LIEBERT,
    parse_liebert_str_without_unit,
    SectionWithoutUnit,
)

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4626 Supply Chilled Water Over Temp
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4626 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4703 Chilled Water Control Valve Failure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4703 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4980 Supply Chilled Water Loss of Flow
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4980 Inactive Event


def inventory_liebert_chilled_water(section: SectionWithoutUnit[str]) -> DiscoveryResult:
    for key in section:
        if key:
            yield Service(item=key)


def check_liebert_chilled_water(item: str, section: SectionWithoutUnit[str]) -> CheckResult:
    if (value := section.get(item)) is None:
        return
    if value.lower() == "inactive event":
        yield Result(state=State.OK, summary="Normal")
    else:
        yield Result(state=State.CRIT, summary="%s" % value)


snmp_section_liebert_chilled_water = SimpleSNMPSection(
    name="liebert_chilled_water",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.100.4626",
            "20.1.2.100.4626",
            "10.1.2.100.4703",
            "20.1.2.100.4703",
            "10.1.2.100.4980",
            "20.1.2.100.4980",
        ],
    ),
    parse_function=parse_liebert_str_without_unit,
)
check_plugin_liebert_chilled_water = CheckPlugin(
    name="liebert_chilled_water",
    service_name="%s",
    discovery_function=inventory_liebert_chilled_water,
    check_function=check_liebert_chilled_water,
)
