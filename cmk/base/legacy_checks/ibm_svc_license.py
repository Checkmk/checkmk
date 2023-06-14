#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.license import license_check_levels
from cmk.base.config import check_info

# Example output from agent:
# <<<ibm_svc_license:sep(58)>>>
# used_flash:0.00
# used_remote:0.00
# used_virtualization:192.94
# license_flash:0
# license_remote:0
# license_virtualization:412
# license_physical_disks:0
# license_physical_flash:off
# license_physical_remote:off
# used_compression_capacity:0.00
# license_compression_capacity:0
# license_compression_enclosures:0


def parse_ibm_svc_license(info):
    licenses = {}
    for line in info:
        if line[0].startswith("license_"):
            license_ = line[0].replace("license_", "")
            if not license_ in licenses:
                licenses[license_] = [0.0, 0.0]
            if line[1] == "off":
                licenses[license_][0] = 0.0
            else:
                licenses[license_][0] = float(line[1])
        if line[0].startswith("used_"):
            license_ = line[0].replace("used_", "")
            if not license_ in licenses:
                licenses[license_] = [0.0, 0.0]
            licenses[license_][1] = float(line[1])
    return licenses


def inventory_ibm_svc_license(parsed):
    for item, data in parsed.items():
        if data != [0.0, 0.0]:
            # Omit unused svc features
            yield item, None


def check_ibm_svc_license(item, params, parsed):
    licensed, used = parsed[item]
    return license_check_levels(licensed, used, params)


check_info["ibm_svc_license"] = LegacyCheckDefinition(
    check_function=check_ibm_svc_license,
    discovery_function=inventory_ibm_svc_license,
    parse_function=parse_ibm_svc_license,
    service_name="License %s",
    check_ruleset_name="ibmsvc_licenses",
)
