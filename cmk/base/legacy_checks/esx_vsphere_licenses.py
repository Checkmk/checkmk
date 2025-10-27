#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Result,
    Service,
    State,
    StringTable,
)

# Example output from agent:
# esx_vsphere_licenses:sep(9)>>>
# VMware vSphere 5 Standard   100 130
# VMware vSphere 5 Enterprise 86 114
# VMware vSphere 5 Enterprise 22 44 # Licenses may appear multiple times (keys different)
# vCenter Server 5 Standard   1 1


@dataclass
class _LicenseCounter:
    used: int = 0
    total: int = 0
    keys: int = 0


type _Section = Mapping[str, _LicenseCounter]


def parse_esx_vsphere_licenses(string_table: StringTable) -> _Section:
    parsed: dict[str, _LicenseCounter] = defaultdict(_LicenseCounter)
    for line in string_table:
        name, values = line
        used, total = values.split()
        parsed[name].used += int(used)
        parsed[name].total += int(total)
        parsed[name].keys += 1
    return parsed


def inventory_esx_vsphere_licenses(section: _Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


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


def check_esx_vsphere_licenses(
    item: str, params: Mapping[str, Any], section: _Section
) -> CheckResult:
    if not (license := section.get(item)):
        return

    yield Result(state=State.OK, summary=f"{license.keys} Key(s)")
    yield Result(state=State.OK, summary=f"Total licenses: {license.total}")
    yield from check_levels(
        license.used,
        metric_name="licenses",
        levels_upper=_make_levels(license.total, params["levels"]),
        label="Used",
        render_func=str,
    )


agent_section_esx_vsphere_licenses = AgentSection(
    name="esx_vsphere_licenses",
    parse_function=parse_esx_vsphere_licenses,
)


check_plugin_esx_vsphere_licenses = CheckPlugin(
    name="esx_vsphere_licenses",
    service_name="License %s",
    discovery_function=inventory_esx_vsphere_licenses,
    check_function=check_esx_vsphere_licenses,
    check_ruleset_name="esx_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
