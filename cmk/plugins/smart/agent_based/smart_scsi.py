#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

from .smart_posix import SCSIAll, SCSIDevice, Section


def discovery_smart_scsi_temp(section: Section) -> DiscoveryResult:
    for disk in section:
        if isinstance(disk.device, SCSIDevice) and disk.temperature is not None:
            yield Service(item=disk.device.name)


def check_smart_scsi_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (disk := _get_disk_scsi(section, item)) is None:
        return

    if disk.temperature is None:
        return

    yield from check_temperature(
        reading=disk.temperature.current,
        params=params,
        unique_name=f"smart_{item}",
        value_store=get_value_store(),
    )


def _get_disk_scsi(section: Section, item: str) -> SCSIAll | None:
    for d in section:
        if isinstance(d.device, SCSIDevice) and d.device.name == item:
            return d

    return None


check_plugin_smart_scsi_temp = CheckPlugin(
    name="smart_scsi_temp",
    sections=["smart_posix_all"],
    service_name="SMART %s Temp",
    discovery_function=discovery_smart_scsi_temp,
    check_function=check_smart_scsi_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
