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
    StringTable,
)
from cmk.plugins.lib.checkpoint import DETECT


def inventory_checkpoint_ha_problems(section: StringTable) -> DiscoveryResult:
    for name, _dev_status, _description in section:
        yield Service(item=name)


def check_checkpoint_ha_problems(item: str, section: StringTable) -> CheckResult:
    for name, dev_status, description in section:
        if name == item:
            if dev_status == "OK":
                yield Result(state=State.OK, summary="OK")
                return
            yield Result(state=State.CRIT, summary=f"{dev_status} - {description}")
            return


def parse_checkpoint_ha_problems(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_checkpoint_ha_problems = SimpleSNMPSection(
    name="checkpoint_ha_problems",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.5.13.1",
        oids=["2", "3", "6"],
    ),
    parse_function=parse_checkpoint_ha_problems,
)
check_plugin_checkpoint_ha_problems = CheckPlugin(
    name="checkpoint_ha_problems",
    service_name="HA Problem %s",
    discovery_function=inventory_checkpoint_ha_problems,
    check_function=check_checkpoint_ha_problems,
)
