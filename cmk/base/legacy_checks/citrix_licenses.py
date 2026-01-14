#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.license import license_check_levels

check_info = {}

# Example output from plugin:
# <<<citrix_licenses>>>
# PVS_STD_CCS 80 0
# PVS_STD_CCS 22 0
# CEHV_ENT_CCS 22 0
# MPS_ENT_CCU 2160 1636
# MPS_ENT_CCU 22 22
# XDT_ENT_UD 22 18
# XDS_ENT_CCS 22 0
# PVSD_STD_CCS 42 0


def parse_citrix_licenses(string_table):
    parsed = {}
    for line in string_table:
        try:
            have = int(line[1])
            used = int(line[2])
        except (IndexError, ValueError):
            continue
        license_type = line[0]
        licenses = parsed.setdefault(license_type, (0, 0))
        parsed[license_type] = (licenses[0] + have, licenses[1] + used)
    return parsed


def discover_citrix_licenses(parsed):
    return [(license_type, {}) for license_type in parsed]


def check_citrix_licenses(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    have, used = data
    if not have:
        yield 3, "No licenses of that type found"
    else:
        yield license_check_levels(have, used, params["levels"][1])


check_info["citrix_licenses"] = LegacyCheckDefinition(
    name="citrix_licenses",
    parse_function=parse_citrix_licenses,
    service_name="Citrix Licenses %s",
    discovery_function=discover_citrix_licenses,
    check_function=check_citrix_licenses,
    check_ruleset_name="citrix_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
