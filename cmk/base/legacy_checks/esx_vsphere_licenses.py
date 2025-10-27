#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from typing import Literal

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import check_levels, LevelsT

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


def _make_levels(
    total: int, params: Literal[False] | tuple[int, int] | tuple[float, float] | None
) -> LevelsT[float]:
    match params:
        case False:
            return ("no_levels", None)
        case None:
            return "fixed", (total, total)
        case int(w), int(c):
            return "fixed", (max(0, total - w), max(0, total - c))
        case float(w), float(c):
            return "fixed", (
                total * (1 - w / 100.0),
                total * (1 - c / 100.0),
            )
        case _:
            return ("no_levels", None)


def check_esx_vsphere_licenses(item, params, parsed):
    if not (license_ := parsed.get(item)):
        return

    yield 0, "%s Key(s)" % license_["keys"]
    yield 0, f"Total licenses: {license_['total']}"
    # we're about to migrate this anyway, but the legacy backend _can_ handle the new classes.
    yield from check_levels(
        license_["used"],
        metric_name="licenses",
        levels_upper=_make_levels(license_["total"], params["levels"]),
        label="Used",
        render_func=str,
    )


check_info["esx_vsphere_licenses"] = LegacyCheckDefinition(
    name="esx_vsphere_licenses",
    parse_function=parse_esx_vsphere_licenses,
    service_name="License %s",
    discovery_function=inventory_esx_vsphere_licenses,
    check_function=check_esx_vsphere_licenses,
    check_ruleset_name="esx_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
