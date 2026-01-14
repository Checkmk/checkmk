#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.dell_om import parse_omreport, status_translate_omreport

check_info = {}

# sample agent output:
#
# <<<omreport_vdisk>>>
# ID                               : 0
# Status                           : Ok
# Name                             : Virtual Disk 0
# State                            : Ready
# Hot Spare Policy violated        : Not Assigned
# Encrypted                        : Not Applicable
# Layout                           : RAID-1
# Size                             : 278.88 GB (299439751168 bytes)
# T10 Protection Information Status : No
# Associated Fluid Cache State     : Not Applicable
# Device Name                      : /dev/sda
# Bus Protocol                     : SAS
# Media                            : HDD
# Read Policy                      : Read Ahead
# Write Policy                     : Write Back
# Cache Policy                     : Not Applicable
# Stripe Element Size              : 64 KB
# Disk Cache Policy                : Unchanged


def discover_dell_om_vdisks(parsed):
    return [(key, None) for key in parsed]


def check_dell_om_vdisks(item, params, parsed):
    if item in parsed:
        status = status_translate_omreport(parsed[item]["Status"])
        if parsed[item]["State"] != "Ready":
            status = 2

        return status, "Device: {}, Status: {}, State: {}, Layout: {}".format(
            parsed[item]["Device Name"],
            parsed[item]["Status"],
            parsed[item]["State"],
            parsed[item]["Layout"],
        )
    return None


check_info["dell_om_vdisks"] = LegacyCheckDefinition(
    name="dell_om_vdisks",
    parse_function=parse_omreport,
    service_name="Virtual Disk %s",
    discovery_function=discover_dell_om_vdisks,
    check_function=check_dell_om_vdisks,
)
