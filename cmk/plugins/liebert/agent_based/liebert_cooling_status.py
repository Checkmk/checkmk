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
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5302 Free Cooling Status
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5302 off


def discover_liebert_cooling_status(section: SectionWithoutUnit[str]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_libert_cooling_status(item: str, section: SectionWithoutUnit[str]) -> CheckResult:
    try:
        yield Result(state=State.OK, summary=section[item])
    except KeyError:
        pass


snmp_section_liebert_cooling_status = SimpleSNMPSection(
    name="liebert_cooling_status",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5302", "20.1.2.1.5302"],
    ),
    parse_function=parse_liebert_str_without_unit,
)
check_plugin_liebert_cooling_status = CheckPlugin(
    name="liebert_cooling_status",
    service_name="%s",
    discovery_function=discover_liebert_cooling_status,
    check_function=check_libert_cooling_status,
)
