#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

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


Section = Mapping[str, tuple[int, int]]


def parse_citrix_licenses(string_table: StringTable) -> Section:
    parsed: dict[str, tuple[int, int]] = {}
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


def discover_citrix_licenses(section: Section) -> DiscoveryResult:
    for license_type in section:
        yield Service(item=license_type)


def _license_levels(
    total: int, params: bool | Sequence[int | float] | None
) -> tuple[float | None, float | None]:
    if params is False:
        return None, None
    if not params:
        return total, total
    if isinstance(params, Sequence) and isinstance(params[0], int):
        return max(0, total - params[0]), max(0, total - params[1])
    if isinstance(params, Sequence):
        return total * (1 - params[0] / 100.0), total * (1 - params[1] / 100.0)
    return None, None


def check_citrix_licenses(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    have, used = data
    if not have:
        yield Result(state=State.UNKNOWN, summary="No licenses of that type found")
        return

    warn, crit = _license_levels(have, params["levels"][1])

    if used <= have:
        infotext = f"used {used} out of {have} licenses"
    else:
        infotext = f"used {used} licenses, but you have only {have}"

    state = State.OK
    if warn is not None and crit is not None:
        if used >= crit:
            state = State.CRIT
        elif used >= warn:
            state = State.WARN
        if state is not State.OK:
            infotext += f" (warn/crit at {int(warn)}/{int(crit)})"

    yield Result(state=state, summary=infotext)
    yield Metric("licenses", used, levels=(warn, crit), boundaries=(0, have))


agent_section_citrix_licenses = AgentSection(
    name="citrix_licenses",
    parse_function=parse_citrix_licenses,
)


check_plugin_citrix_licenses = CheckPlugin(
    name="citrix_licenses",
    service_name="Citrix Licenses %s",
    discovery_function=discover_citrix_licenses,
    check_function=check_citrix_licenses,
    check_ruleset_name="citrix_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
