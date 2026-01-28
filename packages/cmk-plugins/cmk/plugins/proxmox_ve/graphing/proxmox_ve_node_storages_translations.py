#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.graphing.v1.translations import PassiveCheck, RenameToAndScaleBy, ScaleBy, Translation

MIB: Final[float] = 1024.0**2

translation_proxmox_ve_node_storages = Translation(
    name="proxmox_ve_node_storages",
    check_commands=[
        PassiveCheck("proxmox_ve_node_directory_storages"),
        PassiveCheck("proxmox_ve_node_lvm_storages"),
    ],
    translations={
        "fs_used": ScaleBy(MIB),
        "fs_size": ScaleBy(MIB),
        "fs_free": ScaleBy(MIB),
        "growth": RenameToAndScaleBy("fs_growth", MIB / 86400.0),
        "trend": RenameToAndScaleBy("fs_trend", MIB / 86400.0),
        "trend_hoursleft": ScaleBy(3600),
        "uncommitted": ScaleBy(MIB),
    },
)
