#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.license import license_check_levels

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

# <<<rds_licenses:sep(44)>>>
# KeyPackId,Description,KeyPackType,ProductType,ProductVersion,ProductVersionID,TotalLicenses,IssuedLicenses,AvailableLicenses,ExpirationDate
# 13,A02-6.00-S,4,0,Windows Server 2008 oder Windows Server 2008 R2,2,-1,100,-1,01/01/2036 00:00:00
# 2,A02-5.00-EX,6,3,Windows 2000 Server,0,-1,0,-1,01/01/2030 00:00:00
# 3,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,250,250,0,01/02/2045 00:00:00
# 14,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,1050,731,319,01/08/2023 00:00:00
# 16,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,50,23,27,01/04/2026 00:00:00
# 17,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,50,18,32,01/06/2032 00:00:00
# 18,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,65,22,43,01/01/2035 00:00:00
# 19,A02-6.00-S,2,0,Windows Server 2008 oder Windows Server 2008 R2,2,600,0,600,01/01/2036 00:00:00
# 4,C50-6.02-S,2,1,Windows Server 2012,4,300,0,300,01/01/2035 00:00:00
# 3,C50-10.01-S,5,1,Windows Server 2019,6,2000,1,1999,01/01/2031 00:00:00

# Insert any new keys here
# https://msdn.microsoft.com/en-us/library/aa383803%28v=vs.85%29.aspx#properties
rds_licenses_product_versionid_map = {
    "8": "Windows Server 2025",
    "7": "Windows Server 2022",
    "6": "Windows Server 2019",
    "5": "Windows Server 2016",
    "4": "Windows Server 2012",
    "3": "Windows Server 2008 R2",
    "2": "Windows Server 2008",
    # 1    Not supported.
    # 0    Not supported.
}


def parse_rds_licenses(string_table):
    parsed = {}
    if not string_table:
        return parsed
    headers = string_table[0]
    for line in string_table[1:]:
        data = dict(zip(headers, line))
        version_id = data.get("ProductVersionID")
        if version_id not in rds_licenses_product_versionid_map:
            continue
        version = rds_licenses_product_versionid_map[version_id]
        parsed.setdefault(version, [])
        parsed[version].append(data)
    return parsed


def check_rds_licenses(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    total = 0
    used = 0
    for pack in data:
        pack_total = int(pack.get("TotalLicenses"))
        pack_issued = int(pack.get("IssuedLicenses"))
        total += pack_total
        used += pack_issued

    yield license_check_levels(total, used, params["levels"][1])


def discover_rds_licenses(section):
    yield from ((item, {}) for item in section)


check_info["rds_licenses"] = LegacyCheckDefinition(
    name="rds_licenses",
    parse_function=parse_rds_licenses,
    service_name="RDS Licenses %s",
    discovery_function=discover_rds_licenses,
    check_function=check_rds_licenses,
    check_ruleset_name="rds_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
