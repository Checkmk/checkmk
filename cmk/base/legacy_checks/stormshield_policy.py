#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD


def discover_stormshield_policy(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_stormshield_policy(item: str, section: StringTable) -> CheckResult:
    sync_status_mapping = {
        "1": "synced",
        "2": "not synced",
    }
    for line in section:
        policy_name, slot_name, sync_status = line
        if item == policy_name:
            if sync_status == "1":
                yield Result(
                    state=State.OK, summary="Policy is %s" % sync_status_mapping[sync_status]
                )
            else:
                yield Result(
                    state=State.CRIT, summary="Policy is %s" % sync_status_mapping[sync_status]
                )
            if slot_name != "":
                yield Result(state=State.OK, summary="Slot Name: %s" % slot_name)
            else:
                pass


def parse_stormshield_policy(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_stormshield_policy = SimpleSNMPSection(
    name="stormshield_policy",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.8.1.1",
        oids=["2", "3", "5"],
    ),
    parse_function=parse_stormshield_policy,
)


check_plugin_stormshield_policy = CheckPlugin(
    name="stormshield_policy",
    service_name="Policy %s",
    discovery_function=discover_stormshield_policy,
    check_function=check_stormshield_policy,
)
