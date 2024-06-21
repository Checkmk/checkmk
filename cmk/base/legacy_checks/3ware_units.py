#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<3ware_units>>>
# u0    RAID-5    OK             -       -       64K     1788.08   ON     OFF
# u1    RAID-5    INOPERABLE     -       -       64K     1788.08   OFF    OFF

# Different versions of tw_cli have different outputs. This means the size column
# used by this check is in different places. Here is a an example:
#
# Unit  UnitType  Status         %Cmpl  Stripe  Size(GB)  Cache  AVerify IgnECC
# u0    RAID-5    INITIALIZING   84     64K     1396.95   ON     ON      OFF
#
# Unit  UnitType  Status         %RCmpl  %V/I/M  Stripe  Size(GB)  Cache  AVrfy
# u0    RAID-5    OK             -       -       64K     1396.95   ON     ON


# inventory


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_3ware_units(info):
    inventory = []
    for line in info:
        unit = line[0]
        inventory.append((unit, None))
    return inventory


# check
def check_3ware_units(item, _no_params, info):
    for line in info:
        if line[0] == item:
            unit_type = line[1]
            status = line[2]
            complete = line[3]

            # Handle different outputs of tw_cli
            try:
                size = float(line[6])
            except ValueError:
                size = float(line[5])

            complete_txt = ""
            if complete != "-":
                complete_txt = " complete: %s%%" % complete

            infotext = f"{status} (type: {unit_type}, size: {size}GB{complete_txt})"

            if status in ["OK", "VERIFYING"]:
                return (0, "unit status is " + infotext)
            if status in ["INITIALIZING", "VERIFY-PAUSED", "REBUILDING"]:
                return (1, "unit status is " + infotext)
            return (2, "unit status is " + infotext)
    return (3, "unit %s not found in agent output" % item)


# declare the check to Checkmk


def parse_3ware_units(string_table: StringTable) -> StringTable:
    return string_table


check_info["3ware_units"] = LegacyCheckDefinition(
    parse_function=parse_3ware_units,
    service_name="RAID 3ware unit %s",
    discovery_function=inventory_3ware_units,
    check_function=check_3ware_units,
    check_ruleset_name="raid",
)
