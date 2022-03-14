#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<win_video:sep(58)>>>
# Name                 : VirtualBox Graphics Adapter
# Description          : VirtualBox Graphics Adapter
# Caption              : VirtualBox Graphics Adapter
# AdapterCompatibility : Oracle Corporation
# VideoProcessor       :
# DriverVersion        : 4.3.10.0
# DriverDate           : 20140326000000.000000-000
# MaxMemorySupported   :

import time
from typing import Dict, List, Mapping, Optional, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Sequence[Mapping]


def parse_win_video(string_table: StringTable) -> Section:
    videos: List[Dict] = []
    array: Dict = {}
    first_varname = None

    for line in string_table:
        if len(line) < 2:
            continue

        stripped_line = [w.strip() for w in line]
        varname = stripped_line[0]
        value = ":".join(stripped_line[1:])

        if first_varname and varname == first_varname:
            # Looks like we have a new instance
            videos.append(array)
            array = {}

        if not first_varname:
            first_varname = varname

        if varname == "Name":
            array["name"] = value
        elif varname == "DriverVersion":
            array["driver_version"] = value
        elif varname == "DriverDate" and (driver_date := _get_drive_date(value)) is not None:
            array["driver_date"] = driver_date
        elif varname == "AdapterRAM":
            array["graphic_memory"] = _parse_graphic_memory(value)

    # Append last array
    if array:
        videos.append(array)
    return videos


def _parse_graphic_memory(graphic_memory: str) -> int:
    try:
        return int(graphic_memory)
    except ValueError:
        return 0


def _get_drive_date(raw_driver_date: str) -> Optional[int]:
    try:
        return int(time.mktime(time.strptime(raw_driver_date.split(".", 1)[0], "%Y%m%d%H%M%S")))
    except ValueError:
        return None


register.agent_section(
    name="win_video",
    parse_function=parse_win_video,
)


def inventory_win_video(section: Section) -> InventoryResult:
    path = ["hardware", "video"]
    for video in section:
        if "name" in video:
            yield TableRow(
                path=path,
                key_columns={
                    "name": video["name"],
                },
                inventory_columns={
                    "driver_version": video.get("driver_version"),
                    "driver_date": video.get("driver_date"),
                    "graphic_memory": video.get("graphic_memory"),
                },
                status_columns={},
            )


register.inventory_plugin(
    name="win_video",
    inventory_function=inventory_win_video,
)
