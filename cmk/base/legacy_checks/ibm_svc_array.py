#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

# Example output from agent:
# <<<ibm_svc_array:sep(58)>>>
# 27:SSD_mdisk27:online:1:POOL_0_V7000_RZ:372.1GB:online:raid1:1:256:generic_ssd
# 28:SSD_mdisk28:online:2:POOL_1_V7000_BRZ:372.1GB:online:raid1:1:256:generic_ssd
# 29:SSD_mdisk0:online:1:POOL_0_V7000_RZ:372.1GB:online:raid1:1:256:generic_ssd
# 30:SSD_mdisk1:online:2:POOL_1_V7000_BRZ:372.1GB:online:raid1:1:256:generic_ssd


def parse_ibm_svc_array(string_table):
    dflt_header = [
        "mdisk_id",
        "mdisk_name",
        "status",
        "mdisk_grp_id",
        "mdisk_grp_name",
        "capacity",
        "raid_status",
        "raid_level",
        "redundancy",
        "strip_size",
        "tier",
        "encrypt",
    ]
    parsed = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(id_, data)
    return parsed


def check_ibm_svc_array(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    raid_status = data["raid_status"]
    raid_level = data["raid_level"]
    tier = data["tier"]

    # Check raid_status
    message = "Status: %s" % raid_status
    if raid_status == "online":
        status = 0
    elif raid_status in ("offline", "degraded"):
        status = 2
    else:
        status = 1

    # add information
    message += f", RAID Level: {raid_level}, Tier: {tier}"

    yield status, message


def discover_ibm_svc_array(section):
    yield from ((item, {}) for item in section)


check_info["ibm_svc_array"] = LegacyCheckDefinition(
    name="ibm_svc_array",
    parse_function=parse_ibm_svc_array,
    service_name="RAID Array %s",
    discovery_function=discover_ibm_svc_array,
    check_function=check_ibm_svc_array,
)
