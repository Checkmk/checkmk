#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.stormshield import DETECT_STORMSHIELD

check_info = {}


def inventory_stormshield_policy(info):
    for line in info:
        yield (line[0], None)


def check_stormshield_policy(item, _no_params, info):
    sync_status_mapping = {
        "1": "synced",
        "2": "not synced",
    }
    for line in info:
        policy_name, slot_name, sync_status = line
        if item == policy_name:
            if sync_status == "1":
                yield 0, "Policy is %s" % sync_status_mapping[sync_status]
            else:
                yield 2, "Policy is %s" % sync_status_mapping[sync_status]
            if slot_name != "":
                yield 0, "Slot Name: %s" % slot_name
            else:
                pass


def parse_stormshield_policy(string_table: StringTable) -> StringTable:
    return string_table


check_info["stormshield_policy"] = LegacyCheckDefinition(
    name="stormshield_policy",
    parse_function=parse_stormshield_policy,
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.8.1.1",
        oids=["2", "3", "5"],
    ),
    service_name="Policy %s",
    discovery_function=inventory_stormshield_policy,
    check_function=check_stormshield_policy,
)
