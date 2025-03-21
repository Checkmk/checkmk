#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from contextlib import suppress

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)


def parse_win_bios(string_table: StringTable) -> Mapping[str, int | str]:
    section: dict[str, str | int] = {}
    for line in string_table:
        varname = line[0].strip()
        # Separator : seams not ideal. Some systems have : in the BIOS version
        value = ":".join(line[1:]).lstrip()

        if varname == "BIOSVersion":
            section["version"] = value
        elif varname == "SMBIOSBIOSVersion":
            section["smbios_version"] = value
        elif varname == "SMBIOSMajorVersion":
            section["major_version"] = value
        elif varname == "SMBIOSMinorVersion":
            section["minor_version"] = value
        elif varname == "ReleaseDate":
            # The ReleaseDate property indicates the release date of the
            # Win32 BIOS in the Coordinated Universal Time (UTC) format
            # of YYYYMMDDHHMMSS.MMMMMM(+-)OOO.
            date = value.replace("*", "0").split(".", maxsplit=1)[0]
            section["date"] = int(time.mktime(time.strptime(date, "%Y%m%d%H%M%S")))
        elif varname == "Manufacturer":
            section["vendor"] = value
        elif varname == "Name":
            section["model"] = value

    return section


agent_section_win_bios = AgentSection(
    name="win_bios",
    parse_function=parse_win_bios,
)


def inventory_win_bios(section: Mapping[str, str | int]) -> InventoryResult:
    attr = {k: section[k] for k in ("date", "model", "vendor", "version") if k in section}
    with suppress(KeyError):
        attr["version"] = (
            f"{section['smbios_version']} {section['major_version']}.{section['minor_version']}"
        )

    yield Attributes(
        path=["software", "bios"],
        inventory_attributes=attr,
    )


inventory_plugin_win_bios = InventoryPlugin(
    name="win_bios",
    inventory_function=inventory_win_bios,
)
