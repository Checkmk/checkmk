#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import assert_never, Literal, Required, TypedDict

from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.smart.agent_based.smart_posix import ATAAll, NVMeAll, SCSIAll


class DiscoveryParam(TypedDict):
    item_type: Required[tuple[Literal["model_serial", "device_name"], None]]


class TempAndDiscoveredParams(TempParamDict):
    key: Required[tuple[str, str]]


def get_item(
    disk: ATAAll | NVMeAll | SCSIAll, item_type: Literal["model_serial", "device_name"]
) -> str:
    match item_type:
        case "model_serial":
            return f"{disk.model_name} {disk.serial_number}"
        case "device_name":
            return disk.device.name
    assert_never(item_type, f"Implementation error {item_type}")
