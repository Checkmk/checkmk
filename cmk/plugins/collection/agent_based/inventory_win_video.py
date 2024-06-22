#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow

Section = Sequence[Mapping]


def parse_win_video(string_table: StringTable) -> Section:
    videos: list[dict] = []
    array: dict = {}
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


def _get_drive_date(raw_driver_date: str) -> int | None:
    try:
        return int(time.mktime(time.strptime(raw_driver_date.split(".", 1)[0], "%Y%m%d%H%M%S")))
    except ValueError:
        return None


agent_section_win_video = AgentSection(
    name="win_video",
    parse_function=parse_win_video,
)


def inventory_win_video(section: Section) -> InventoryResult:
    for video in section:
        if "name" in video:
            yield TableRow(
                path=["hardware", "video"],
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


inventory_plugin_win_video = InventoryPlugin(
    name="win_video",
    inventory_function=inventory_win_video,
)
