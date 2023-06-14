#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Note: this check is deprecated. It is superseeded by the new
# Check_MK HW/SW-Inventory.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_dmi_sysinfo(info):
    if len(info) > 0 and info[0] == ["System", "Information"]:
        return [(None, None)]
    return []


def check_dmi_sysinfo(item, param, info):
    if len(info) == 0 or info[0] != ["System", "Information"]:
        return (3, "Invalid information")
    data = {}
    for line in info:
        line = " ".join(line)
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()

    return (
        0,
        "Manufacturer: %s, Product-Name: %s, Version: %s, S/N: %s"
        % (
            data.get("Manufacturer", "Unknown"),
            data.get("Product Name", "Unknown"),
            data.get("Version", "Unknown"),
            data.get("Serial Number", "Unknown"),
        ),
    )


check_info["dmi_sysinfo"] = LegacyCheckDefinition(
    check_function=check_dmi_sysinfo,
    discovery_function=inventory_dmi_sysinfo,
    service_name="DMI Sysinfo",
)
