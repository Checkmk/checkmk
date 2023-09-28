#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.2.0 1996492800
# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.2.1 1996492801
# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.3.0 1
# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.3.1 4
# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.5.0 49
# .1.3.6.1.4.1.211.1.21.1.150.2.22.2.1.5.1 -1

from collections.abc import Mapping
from typing import NamedTuple

from .agent_based_api.v1 import (
    check_levels,
    equals,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

FJDARYE_SUPPORTED_DEVICE = ".1.3.6.1.4.1.211.1.21.1.150"  # fjdarye500


class PCIeFlashModule(NamedTuple):
    module_id: str
    status: str
    health_lifetime: float


PCIeFlashModuleSection = Mapping[str, PCIeFlashModule]

MAP_STATES = {
    "1": Result(state=State.OK, summary="Status: normal"),
    "2": Result(state=State.CRIT, summary="Status: alarm"),
    "3": Result(state=State.WARN, summary="Status: warning"),
    "4": Result(state=State.CRIT, summary="Status: invalid"),
    "5": Result(state=State.OK, summary="Status: maintenance"),
    "6": Result(state=State.UNKNOWN, summary="Status: undefined"),
}


def parse_fjdarye_pcie_flash_modules(string_table: list[StringTable]) -> PCIeFlashModuleSection:
    if not string_table:
        return {}

    return {
        module_id: PCIeFlashModule(module_id, status, float(health_lifetime))
        for module_id, status, health_lifetime in string_table[0]
    }


register.snmp_section(
    name="fjdarye_pcie_flash_modules",
    parse_function=parse_fjdarye_pcie_flash_modules,
    fetch=[
        SNMPTree(
            base=f"{FJDARYE_SUPPORTED_DEVICE}.2.22.2.1",
            oids=[
                "2",  # FJDARY-E150::fjdaryPfmItemId
                "3",  # FJDARY-E150::fjdaryPfmStatus
                "5",  # FJDARY-E150::fjdaryPfmHealth
            ],
        )
    ],
    detect=equals(".1.3.6.1.2.1.1.2.0", FJDARYE_SUPPORTED_DEVICE),
)


def discover_fjdarye_pcie_flash_modules(section: PCIeFlashModuleSection) -> DiscoveryResult:
    for module in section.values():
        if module.status != "4":
            yield Service(item=module.module_id)


def check_fjdarye_pcie_flash_modules(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: PCIeFlashModuleSection,
) -> CheckResult:
    if (module := section.get(item)) is None:
        return

    yield MAP_STATES[module.status]

    if module.health_lifetime < 0:
        yield Result(
            state=State.OK,
            summary="Health lifetime cannot be obtained",
        )
        return

    yield from check_levels(
        value=module.health_lifetime,
        levels_lower=params["health_lifetime_perc"],
        label="Health lifetime",
        render_func=render.percent,
    )


register.check_plugin(
    name="fjdarye_pcie_flash_modules",
    service_name="PCIe flash module %s",
    discovery_function=discover_fjdarye_pcie_flash_modules,
    check_function=check_fjdarye_pcie_flash_modules,
    check_ruleset_name="pfm_health",
    check_default_parameters={"health_lifetime_perc": (20.0, 15.0)},
)
