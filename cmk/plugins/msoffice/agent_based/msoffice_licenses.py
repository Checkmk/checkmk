#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<msoffice_licenses>>>
# mggraph:VISIOCLIENT 11 0 10
# mggraph:POWER_BI_PRO 13 0 11
# mggraph:WINDOWS_STORE 1000000 0 0
# mggraph:ENTERPRISEPACK 1040 1 395
# mggraph:FLOW_FREE 10000 0 11
# mggraph:EXCHANGESTANDARD 5 0 2
# mggraph:POWER_BI_STANDARD 1000000 0 18
# mggraph:EMS 1040 0 991
# mggraph:RMSBASIC 1 0 0
# mggraph:PROJECTPROFESSIONAL 10 0 10
# mggraph:ATP_ENTERPRISE 1040 0 988

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


def parse_msoffice_licenses(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}

    for line in string_table:
        if len(line) >= 1 and "Microsoft.Graph module is not installed" in " ".join(line):
            return {
                "_error": "MS Office agent plugin requires installation of the Powershell Module Microsoft.Graph for all users, see werk #18609"
            }

        if len(line) != 4:
            continue

        try:
            parsed.setdefault(
                line[0],
                {"active": int(line[1]), "warning_units": int(line[2]), "consumed": int(line[3])},
            )
        except ValueError:
            pass

    return parsed


def discover_msoffice_licenses(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_msoffice_licenses(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if "_error" in section:
        yield Result(state=State.CRIT, summary=str(section["_error"]))
        return
    if not (item_data := section.get(item)):
        return
    lcs_active = item_data["active"]
    lcs_consumed = item_data["consumed"]

    if not lcs_active:
        yield Result(state=State.OK, summary="No active licenses")
        return

    warn, crit = params["usage"]
    levels_abs: tuple[float, float] | None = None
    levels_perc: tuple[float, float] | None = None
    if isinstance(warn, float):
        levels_perc = (warn, crit)
    else:
        levels_abs = (warn, crit)

    # the agent plug-in also gathers the last 3 unused licenses with no
    # active licenses. To handle this, we only output consumed licenses for
    # licenses with active ones
    yield from check_levels(
        lcs_consumed,
        levels_upper=levels_abs,
        metric_name="licenses",
        render_func=lambda v: str(int(v)),
        label="Consumed licenses",
    )

    yield Result(state=State.OK, summary=f"Active licenses: {lcs_active}")
    yield Metric("licenses_total", lcs_active)

    usage = lcs_consumed * 100.0 / lcs_active
    yield from check_levels(
        usage,
        levels_upper=levels_perc,
        metric_name="license_percentage",
        render_func=render.percent,
        label="Usage",
        boundaries=(0, 100),
    )

    lcs_warning_units = item_data["warning_units"]
    if lcs_warning_units:
        yield Result(state=State.OK, summary=f" Warning units: {lcs_warning_units}")


agent_section_msoffice_licenses = AgentSection(
    name="msoffice_licenses",
    parse_function=parse_msoffice_licenses,
)


check_plugin_msoffice_licenses = CheckPlugin(
    name="msoffice_licenses",
    service_name="MS Office Licenses %s",
    discovery_function=discover_msoffice_licenses,
    check_function=check_msoffice_licenses,
    check_ruleset_name="msoffice_licenses",
    check_default_parameters={
        "usage": (80.0, 90.0),
    },
)
