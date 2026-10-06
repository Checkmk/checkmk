#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

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


@dataclass(frozen=True)
class License:
    licensed: float
    used: float


Section = Mapping[str, License]


class IbmSvcLicenseParams(TypedDict):
    levels: tuple[str, object]


def parse_ibm_svc_license(string_table: StringTable) -> Section:
    licenses: dict[str, list[float]] = {}
    for line in string_table:
        if line[0].startswith("license_"):
            license_ = line[0].replace("license_", "")
            licenses.setdefault(license_, [0.0, 0.0])
            licenses[license_][0] = 0.0 if line[1] == "off" else float(line[1])
        if line[0].startswith("used_"):
            license_ = line[0].replace("used_", "")
            licenses.setdefault(license_, [0.0, 0.0])
            licenses[license_][1] = float(line[1])
    return {item: License(licensed=data[0], used=data[1]) for item, data in licenses.items()}


def discover_ibm_svc_license(section: Section) -> DiscoveryResult:
    # Omit unused svc features
    yield from (
        Service(item=item)
        for item, data in section.items()
        if data.licensed != 0.0 or data.used != 0.0
    )


def _compute_levels(
    licensed: float, level_spec: tuple[str, object]
) -> tuple[float | None, float | None]:
    kind, value = level_spec
    if kind == "crit_on_all":
        return licensed, licensed
    if kind == "absolute" and isinstance(value, dict):
        return max(0.0, licensed - value["warn"]), max(0.0, licensed - value["crit"])
    if kind == "percentage" and isinstance(value, dict):
        return licensed * (1 - value["warn"] / 100.0), licensed * (1 - value["crit"] / 100.0)
    # "always_ok" and any unexpected configuration impose no levels.
    return None, None


def check_ibm_svc_license(item: str, params: IbmSvcLicenseParams, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    licensed, used = data.licensed, data.used

    warn, crit = _compute_levels(licensed, params["levels"])

    if used <= licensed:
        summary = f"used {int(used)} out of {int(licensed)} licenses"
    else:
        summary = f"used {int(used)} licenses, but you have only {int(licensed)}"

    state = State.OK
    if warn is not None and crit is not None:
        if used >= crit:
            state = State.CRIT
        elif used >= warn:
            state = State.WARN
        if state is not State.OK:
            summary += f" (warn/crit at {int(warn)}/{int(crit)})"

    yield Result(state=state, summary=summary)
    yield Metric("licenses", used, levels=_metric_levels(warn, crit), boundaries=(0, licensed))


def _metric_levels(warn: float | None, crit: float | None) -> tuple[float, float] | None:
    if warn is None or crit is None:
        return None
    return warn, crit


agent_section_ibm_svc_license = AgentSection(
    name="ibm_svc_license",
    parse_function=parse_ibm_svc_license,
)


check_plugin_ibm_svc_license = CheckPlugin(
    name="ibm_svc_license",
    service_name="License %s",
    discovery_function=discover_ibm_svc_license,
    check_function=check_ibm_svc_license,
    check_ruleset_name="ibmsvc_licenses",
    check_default_parameters={"levels": ("crit_on_all", None)},
)
