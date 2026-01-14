#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib import ucd_hr_detection

check_info = {}

# .1.3.6.1.4.1.2021.9.1.2.1 /         --> UCD-SNMP-MIB::dskPath.1
# .1.3.6.1.4.1.2021.9.1.6.1 958827968 --> UCD-SNMP-MIB::dskTotal.1
# .1.3.6.1.4.1.2021.9.1.7.1 55330132  --> UCD-SNMP-MIB::dskAvail.1


def discover_ucd_disk(info):
    return [(line[0], {}) for line in info]


def check_ucd_disk(item, params, info):
    """Provided elements are
    2: dskPath
    6: dskTotal (kb)
    7: dskAvail (kb)
    see https://oidref.com/1.3.6.1.4.1.2021.9.1
    """
    for disk_path, disk_total_kb_str, disk_avail_kb_str in info:
        if disk_path == item:
            return df_check_filesystem_single(
                mountpoint=item,
                size_mb=float(disk_total_kb_str) / 1024,
                avail_mb=float(disk_avail_kb_str) / 1024,
                reserved_mb=0,
                inodes_total=None,
                inodes_avail=None,
                params=params,
            )
    return None


def parse_ucd_disk(string_table: StringTable) -> StringTable:
    return string_table


check_info["ucd_disk"] = LegacyCheckDefinition(
    name="ucd_disk",
    parse_function=parse_ucd_disk,
    detect=ucd_hr_detection.PREFER_HR_ELSE_UCD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.9.1",
        oids=["2", "6", "7"],
    ),
    service_name="Filesystem %s",
    discovery_function=discover_ucd_disk,
    check_function=check_ucd_disk,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
