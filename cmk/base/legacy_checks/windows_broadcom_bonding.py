#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<windows_broadcom_bonding>>>
# Caption            RedundancyStatus
# BOND_10.3          2
# BOND_HeartbeatMS   2
#


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_windows_broadcom_bonding(info):
    inventory = []
    for line in info[1:]:
        inventory.append((" ".join(line[:-1]), None))
    return inventory


def check_windows_broadcom_bonding(item, params, info):
    for line in info:
        if " ".join(line[:-1]) == item:
            status = int(line[-1])
            if status == 5:
                return 2, "Bond not working"
            if status == 4:
                return 1, "Bond partly working"
            if status == 2:
                return 0, "Bond fully working"
            return 3, "Bond status cannot be recognized"
    return 3, "Bond %s not found in agent output" % item


def parse_windows_broadcom_bonding(string_table: StringTable) -> StringTable:
    return string_table


check_info["windows_broadcom_bonding"] = LegacyCheckDefinition(
    name="windows_broadcom_bonding",
    parse_function=parse_windows_broadcom_bonding,
    service_name="Bonding Interface %s",
    discovery_function=discover_windows_broadcom_bonding,
    check_function=check_windows_broadcom_bonding,
)
