#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.license import license_check_levels

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

# Example output from agent:
# esx_vsphere_licenses:sep(9)>>>
# VMware vSphere 5 Standard   100 130
# VMware vSphere 5 Enterprise 86 114
# VMware vSphere 5 Enterprise 22 44 # Licenses may appear multiple times (keys different)
# vCenter Server 5 Standard   1 1


def parse_esx_vsphere_licenses(string_table):
    parsed = {}
    for line in string_table:
        name, values = line
        parsed.setdefault(name, {"used": 0, "total": 0, "keys": 0})
        used, total = values.split()
        parsed[name]["used"] += int(used)
        parsed[name]["total"] += int(total)
        parsed[name]["keys"] += 1
    return parsed


def inventory_esx_vsphere_licenses(parsed):
    return [(key, {}) for key in parsed]


def check_esx_vsphere_licenses(item, params, parsed):
    license_ = parsed.get(item)
    if not license_:
        return 3, "License not found in agent output"

    status, infotext, perfdata = license_check_levels(
        license_["total"], license_["used"], params["levels"][1]
    )
    infotext = "%s Key(s), " % license_["keys"] + infotext
    return status, infotext, perfdata


check_info["esx_vsphere_licenses"] = LegacyCheckDefinition(
    name="esx_vsphere_licenses",
    parse_function=parse_esx_vsphere_licenses,
    service_name="License %s",
    discovery_function=inventory_esx_vsphere_licenses,
    check_function=check_esx_vsphere_licenses,
    check_ruleset_name="esx_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
