#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from collections.abc import Sequence

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


def license_check_levels(
    total: int, in_use: int, params: bool | Sequence[int | float] | None
) -> tuple[int, str, list[tuple[str, int, float | None, float | None, int, int]]]:
    if params is False:
        warn: float | None = None
        crit: float | None = None
    elif not params:
        warn = total
        crit = total
    elif isinstance(params, Sequence) and isinstance(params[0], int):
        warn = max(0, total - params[0])
        crit = max(0, total - params[1])
    elif isinstance(params, Sequence):
        warn = total * (1 - params[0] / 100.0)
        crit = total * (1 - params[1] / 100.0)
    else:
        warn = None
        crit = None

    perfdata = [("licenses", in_use, warn, crit, 0, total)]
    if in_use <= total:
        infotext = "used %d out of %d licenses" % (in_use, total)
    else:
        infotext = "used %d licenses, but you have only %d" % (in_use, total)

    status = 0
    if warn is not None and crit is not None:
        if in_use >= crit:
            status = 2
        elif in_use >= warn:
            status = 1
        if status:
            infotext += f" (warn/crit at {int(warn)}/{int(crit)})"

    return status, infotext, perfdata


def check_esx_vsphere_licenses(item, params, parsed):
    if not (license_ := parsed.get(item)):
        return

    yield 0, "%s Key(s)" % license_["keys"]
    yield license_check_levels(license_["total"], license_["used"], params["levels"][1])


check_info["esx_vsphere_licenses"] = LegacyCheckDefinition(
    name="esx_vsphere_licenses",
    parse_function=parse_esx_vsphere_licenses,
    service_name="License %s",
    discovery_function=inventory_esx_vsphere_licenses,
    check_function=check_esx_vsphere_licenses,
    check_ruleset_name="esx_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
