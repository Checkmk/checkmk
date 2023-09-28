#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils import ucd_hr_detection

# .1.3.6.1.4.1.2021.9.1.2.1 /         --> UCD-SNMP-MIB::dskPath.1
# .1.3.6.1.4.1.2021.9.1.6.1 958827968 --> UCD-SNMP-MIB::dskTotal.1
# .1.3.6.1.4.1.2021.9.1.7.1 55330132  --> UCD-SNMP-MIB::dskAvail.1


def inventory_ucd_disk(info):
    return [(line[0], {}) for line in info]


def check_ucd_disk(item, params, info):
    for disk_path, disk_total_str, disk_avail_str in info:
        if disk_path == item:
            disk_total_mb = float(disk_total_str) / 1024
            disk_avail_mb = float(disk_avail_str) / 1024
            return df_check_filesystem_single(
                item, disk_total_mb, disk_avail_mb, 0, None, None, params
            )
    return None


check_info["ucd_disk"] = LegacyCheckDefinition(
    detect=ucd_hr_detection.PREFER_HR_ELSE_UCD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.9.1",
        oids=["2", "6", "7"],
    ),
    service_name="Filesystem %s",
    discovery_function=inventory_ucd_disk,
    check_function=check_ucd_disk,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
