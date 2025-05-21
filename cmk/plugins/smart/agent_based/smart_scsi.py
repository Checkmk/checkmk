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
    ServiceLabel,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

from .smart_posix import SCSIAll, SCSIDevice, Section


def discovery_smart_scsi_temp(
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for item, disk in devices.items():
        if isinstance(disk.device, SCSIDevice) and disk.temperature is not None:
            # On a controller temperature is set to zero, see `scsiCheckIE` in `smartmoontools`.
            # These are not values reported by the drive, but rather values made up by `smartctl`.
            if disk.temperature.current == 0 and disk.temperature.drive_trip == 0:
                continue
            if (
                disk.temperature.current == 0
                and disk.scsi_temperature is not None
                and disk.scsi_temperature.drive_trip == 0
            ):
                continue
            yield Service(
                item=item,
                labels=[
                    ServiceLabel("cmk/smart/type", "SCSI"),
                    ServiceLabel("cmk/smart/device", disk.device.name),
                    ServiceLabel("cmk/smart/model", disk.model_name),
                    ServiceLabel("cmk/smart/serial", disk.serial_number),
                ],
            )


def check_smart_scsi_temp(
    item: str,
    params: TempParamDict,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if not isinstance(disk := devices.get(item), SCSIAll) or disk.temperature is None:
        return

    yield from check_temperature(
        reading=disk.temperature.current,
        params=params,
        unique_name=f"smart_{item}",
        value_store=get_value_store(),
    )


check_plugin_smart_scsi_temp = CheckPlugin(
    name="smart_scsi_temp",
    sections=["smart_posix_all", "smart_posix_scan_arg"],
    service_name="Temperature SMART %s",
    discovery_function=discovery_smart_scsi_temp,
    check_function=check_smart_scsi_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
