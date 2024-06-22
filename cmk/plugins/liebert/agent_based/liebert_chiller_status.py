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
    startswith,
    State,
    StringTable,
)


def inventory_liebert_chiller_status(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_liebert_chiller_status(section: StringTable) -> CheckResult:
    status = section[0][0]
    if status not in ["5", "7"]:
        yield Result(state=State.CRIT, summary="Device is in a non OK state")
    else:
        yield Result(state=State.OK, summary="Device is in a OK state")


def parse_liebert_chiller_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_liebert_chiller_status = SimpleSNMPSection(
    name="liebert_chiller_status",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.476.1.42.4.3.20"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.4.3.20.1.1.20",
        oids=["2"],
    ),
    parse_function=parse_liebert_chiller_status,
)
check_plugin_liebert_chiller_status = CheckPlugin(
    name="liebert_chiller_status",
    service_name="Chiller status",
    discovery_function=inventory_liebert_chiller_status,
    check_function=check_liebert_chiller_status,
)
