#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<win_system:sep(58)>>>
# Manufacturer : Oracle Corporation
# Name         : Computergehäuse
# Model        :
# HotSwappable :
# InstallDate  :
# PartNumber   :
# SerialNumber :

import dataclasses
import re

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)


@dataclasses.dataclass
class Section:
    serial: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    family: str | None = None


def parse(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if len(line) > 2:
            line = [line[0], ":".join(line[1:])]
        varname, value = line
        varname = re.sub(" *", "", varname)
        value = re.sub("^ ", "", value)
        if varname == "SerialNumber":
            section.serial = value
        elif varname == "Manufacturer":
            section.manufacturer = value
        elif varname == "Name":
            section.product = value
        elif varname == "Model":
            section.family = value
    return section


agent_section_win_system = AgentSection(
    name="win_system",
    parse_function=parse,
)


def inventory(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes=dataclasses.asdict(section),
    )


inventory_plugin_win_system = InventoryPlugin(
    name="win_system",
    inventory_function=inventory,
)
