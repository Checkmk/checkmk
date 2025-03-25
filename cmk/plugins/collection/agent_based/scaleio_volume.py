#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy
from cmk.plugins.lib.scaleio import (
    create_disk_read_write,
    DiskReadWrite,
    parse_scaleio,
    StorageConversionError,
)

# <<<scaleio_volume>>>
# VOLUME f6a9425800000002:
#        ID                                                 f6a9425800000002
#        NAME                                               SEASIOCF1001
#        SIZE                                               8.0 TB (8192 GB)
#        USER_DATA_READ_BWC                                 0 IOPS 0 Bytes per-second
#        USER_DATA_WRITE_BWC                                0 IOPS 0 Bytes per-second
#
# VOLUME f6a9425900000003:
#        ID                                                 f6a9425900000003
#        NAME                                               SEASIOCF2001
#        SIZE                                               5.0 TB (5120 GB)
#        USER_DATA_READ_BWC                                 0 IOPS 0 Bytes per-second
#        USER_DATA_WRITE_BWC                                0 IOPS 0 Bytes per-second
#


class ScaleioVolume(NamedTuple):
    volume_id: str
    name: str
    size: float
    size_unit: str
    volume_ios: DiskReadWrite | StorageConversionError


ScaleioVolumeSection = Mapping[str, ScaleioVolume]


def parse_scaleio_volume(string_table: StringTable) -> ScaleioVolumeSection:
    section: dict[str, ScaleioVolume] = {}

    for volume_id, volume in parse_scaleio(string_table, "VOLUME").items():
        section[volume_id] = ScaleioVolume(
            volume_id=volume_id,
            name=volume["NAME"][0],
            size=float(volume["SIZE"][0]),
            size_unit=volume["SIZE"][1],
            volume_ios=create_disk_read_write(
                volume["USER_DATA_READ_BWC"],
                volume["USER_DATA_WRITE_BWC"],
            ),
        )

    return section


agent_section_scaleio_volume = AgentSection(
    name="scaleio_volume",
    parse_function=parse_scaleio_volume,
)


def discover_scaleio_volume(section: ScaleioVolumeSection) -> DiscoveryResult:
    yield from (Service(item=volume_id) for volume_id in section)


def check_scaleio_volume(
    item: str,
    params: Mapping[str, Any],
    section: ScaleioVolumeSection,
) -> CheckResult:
    change_unit = {
        "KB": "MB",
        "MB": "GB",
        "GB": "TB",
    }
    if not (volume := section.get(item)):
        return

    total = volume.size
    unit = volume.size_unit
    # Assuming the API will never report
    # a number bigger than 1048576
    if total > 1024:
        total = total // 1024
        unit = change_unit[unit]
    yield Result(
        state=State.OK,
        summary=f"Name: {volume.name}, Size: {total:.1f} {unit}",
    )

    if isinstance(volume.volume_ios, StorageConversionError):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Unknown unit: {volume.volume_ios.unit}",
        )
        return

    yield from check_diskstat_dict_legacy(
        params=params,
        disk={
            "read_ios": volume.volume_ios.read_operations,
            "read_throughput": volume.volume_ios.read_throughput,
            "write_ios": volume.volume_ios.write_operations,
            "write_throughput": volume.volume_ios.write_throughput,
        },
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_scaleio_volume = CheckPlugin(
    name="scaleio_volume",
    service_name="ScaleIO Volume %s",
    check_function=check_scaleio_volume,
    discovery_function=discover_scaleio_volume,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
