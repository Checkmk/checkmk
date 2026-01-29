#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import (
    check_temperature,
    OptFloat,
    TempParamType,
)

check_info = {}

# EXAMPLE DATA FROM: WDC SSC-D0128SC-2100
# <<<smart>>>
# /dev/sda ATA WDC_SSC-D0128SC-   1 Raw_Read_Error_Rate     0x000b   100   100   050    Pre-fail  Always       -       16777215
# /dev/sda ATA WDC_SSC-D0128SC-   3 Spin_Up_Time            0x0007   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   7 Seek_Error_Rate         0x000b   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       1408
# /dev/sda ATA WDC_SSC-D0128SC-  10 Spin_Retry_Count        0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       523
# /dev/sda ATA WDC_SSC-D0128SC- 168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1
# /dev/sda ATA WDC_SSC-D0128SC- 175 Program_Fail_Count_Chip 0x0003   100   100   010    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 192 Power-Off_Retract_Count 0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 194 Temperature_Celsius     0x0022   040   100   000    Old_age   Always       -       40 (Lifetime Min/Max 30/60)
# /dev/sda ATA WDC_SSC-D0128SC- 197 Current_Pending_Sector  0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 240 Head_Flying_Hours       0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 170 Unknown_Attribute       0x0003   100   100   010    Pre-fail  Always       -       1769478
# /dev/sda ATA WDC_SSC-D0128SC- 173 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4217788040605


def discover_smart_temp(
    section: Mapping[str, Mapping[str, int]],
) -> Generator[tuple[str, dict[str, Any]]]:
    relevant = {"Temperature_Celsius", "Temperature_Internal", "Temperature"}
    for disk_name, disk in section.items():
        if relevant.intersection(disk):
            yield disk_name, {}


def check_smart_temp(
    item: str,
    params: TempParamType,
    section: Mapping[str, Mapping[str, int]],
) -> tuple[int, str, list[tuple[str, float, OptFloat, OptFloat, OptFloat, OptFloat]]] | None:
    if (data := section.get(item)) is None:
        return None

    if (temperature := data.get("Temperature")) is None:
        return None

    return check_temperature(temperature, params, "smart_%s" % item)


check_info["smart.temp"] = LegacyCheckDefinition(
    name="smart_temp",
    # section already migrated!
    service_name="Temperature SMART %s",
    sections=["smart"],  # This agent plugin was superseded by smart_posix
    discovery_function=discover_smart_temp,
    check_function=check_smart_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
