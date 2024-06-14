#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)

Section = Mapping[str, str]


def parse_ipmi_firmware(string_table: StringTable) -> Section:
    section = {"type": "IPMI"}

    for line in string_table:
        if line[0] == "BMC Version" and line[1] == "version":
            section["version"] = line[2]

    return section


agent_section_ipmi_firmware = AgentSection(
    name="ipmi_firmware",
    parse_function=parse_ipmi_firmware,
)


def inventory_ipmi_firmware(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "management_interface"],
        inventory_attributes=section,
    )


inventory_plugin_ipmi_firmware = InventoryPlugin(
    name="ipmi_firmware",
    inventory_function=inventory_ipmi_firmware,
)
