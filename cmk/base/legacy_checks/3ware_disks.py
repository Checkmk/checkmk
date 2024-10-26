#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<3ware_disks>>>
# p0     OK               u1     298.09 GB   625142448     WD-WCAT19310918
# p1     OK               u0     298.09 GB   625142448     WD-WCARW3200306
# p2     OK               u0     298.09 GB   625142448     WD-WCARW3006518
# p3     OK               u0     298.09 GB   625142448     WD-WCARW3199987

# Another example:
# p0     OK               u0     298.09 GB   625142448     WD-WCAPD4348449
# p1     OK               u0     298.09 GB   625142448     WD-WCAPD4168681
# p2     OK               u0     298.09 GB   625142448     WD-WCAPD4164590
# p3     OK               u1     298.09 GB   625142448     WD-WCAPD4163656
# p4     OK               u0     298.09 GB   625142448     WD-WCAPD4160960
# p5     OK               u0     298.09 GB   625142448     WD-WCAPD4164594

# Some more data
# Port   Status           Unit   Size        Blocks        Serial
# ---------------------------------------------------------------
# p0     OK               u0     233.81 GB   490350672     WD-WCAT1E297748
# p1     OK               u0     233.81 GB   490350672     WD-WCAT1E314892
# p2     OK               u2     233.81 GB   490350672     WD-WCAT1E313303
# p3     OK               u1     931.51 GB   1953525168    9QJ56A1M
# p4     OK               u1     931.51 GB   1953525168    9QJ2WPCR
# p5     OK               u1     931.51 GB   1953525168    9QJ2DG9C
# p6     NOT-PRESENT      -      -           -             -
# p7     NOT-PRESENT      -      -           -             -


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_3ware_disks(info):
    inventory = []
    for line in info:
        if len(line) > 0:
            if line[1] == "NOT-PRESENT":
                continue
            disk = line[0]
            inventory.append((disk, {}))
    return inventory


def check_3ware_disks(item, _no_params, info):
    for line in info:
        if line[0] != item:
            continue

        status = line[1]
        unit_type = line[2]
        size = line[3]
        size_type = line[4]
        disk_type = line[5]
        model = line[-1]
        infotext = f"{status} (unit: {unit_type}, size: {size},{size_type}, type: {disk_type}, model: {model})"
        if status in ["OK", "VERIFYING"]:
            return (0, "disk status is " + infotext)
        if status in ["SMART_FAILURE"]:
            return (1, "disk status is " + infotext)
        return (2, "disk status is " + infotext)

    return (3, "disk %s not found in agent output" % item)


# declare the check to Checkmk


def parse_3ware_disks(string_table: StringTable) -> StringTable:
    return string_table


check_info["3ware_disks"] = LegacyCheckDefinition(
    name="3ware_disks",
    parse_function=parse_3ware_disks,
    service_name="RAID 3ware disk %s",
    discovery_function=inventory_3ware_disks,
    check_function=check_3ware_disks,
    check_ruleset_name="raid_disk",
)
