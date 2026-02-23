#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.checkpoint.lib import DETECT


def discover_checkpoint_powersupply(section: StringTable) -> DiscoveryResult:
    for index, _dev_status in section:
        yield Service(item=index)


def check_checkpoint_powersupply(
    item: str, params: Mapping[str, object], section: StringTable
) -> CheckResult:
    for index, dev_status in section:
        if index == item:
            yield Result(
                state=State(params.get(dev_status.lower(), State.CRIT)),
                summary=dev_status,
            )
            return


def parse_checkpoint_powersupply(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_checkpoint_powersupply = SimpleSNMPSection(
    name="checkpoint_powersupply",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.9.1.1",
        oids=["1", "2"],
    ),
    parse_function=parse_checkpoint_powersupply,
)
check_plugin_checkpoint_powersupply = CheckPlugin(
    name="checkpoint_powersupply",
    service_name="Power Supply %s",
    discovery_function=discover_checkpoint_powersupply,
    check_function=check_checkpoint_powersupply,
    # for possible device statuses see SUP-27826
    # only "Present" seems officially supported, but we've also seen "up"
    check_default_parameters={
        "up": State.OK.value,
        "present": State.CRIT.value,
    },
    check_ruleset_name="checkpoint_powersupply",
)
