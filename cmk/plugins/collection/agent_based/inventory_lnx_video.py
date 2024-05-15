#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output
# <<<lnx_video>>>
# 05:00.0 VGA compatible controller: Advanced Micro Devices [AMD] nee ATI Cape Verde PRO [Radeon HD 7700 Series] (prog-if 00 [VGA controller])
#        Subsystem: Hightech Information System Ltd. Device 200b
#        Flags: bus master, fast devsel, latency 0, IRQ 58
#        Memory at d0000000 (64-bit, prefetchable) [size=256M]
#        Memory at fe8c0000 (64-bit, non-prefetchable) [size=256K]
#        I/O ports at c000 [size=256]
#        Expansion ROM at fe8a0000 [disabled] [size=128K]
#        Capabilities: [48] Vendor Specific Information: Len=08 <?>
#        Capabilities: [50] Power Management version 3
#        Capabilities: [58] Express Legacy Endpoint, MSI 00
#        Capabilities: [a0] MSI: Enable+ Count=1/1 Maskable- 64bit+
#        Capabilities: [100] Vendor Specific Information: ID=0001 Rev=1 Len=010 <?>
#        Capabilities: [150] Advanced Error Reporting
#        Capabilities: [270] #19
#        Kernel driver in use: fglrx_pci

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow


@dataclass
class GraphicsCard:
    name: str
    subsystem: str | None = None
    driver: str | None = None


Section = Mapping[str, GraphicsCard]


def parse_lnx_video(string_table: StringTable) -> Section:
    parsed_section: dict[str, GraphicsCard] = {}

    current_name: str = ""
    for line in string_table:
        if len(line) <= 1:
            continue

        if "VGA compatible controller" in line[-2]:
            current_name = line[-1].strip()
            if current_name:
                parsed_section.setdefault(current_name, GraphicsCard(name=current_name))
        elif current_name:
            if line[0] == "Subsystem":
                parsed_section[current_name].subsystem = line[1].strip()
            elif line[0] == "Kernel driver in use":
                parsed_section[current_name].driver = line[1].strip()

    return parsed_section


agent_section_lnx_video = AgentSection(
    name="lnx_video",
    parse_function=parse_lnx_video,
)


def inventory_lnx_video(section: Section) -> InventoryResult:
    for graphics_card in section.values():
        if graphics_card.name:
            yield TableRow(
                path=["hardware", "video"],
                key_columns={
                    "name": graphics_card.name,
                },
                inventory_columns={
                    "subsystem": graphics_card.subsystem,
                    "driver": graphics_card.driver,
                },
                status_columns={},
            )


inventory_plugin_lnx_video = InventoryPlugin(
    name="lnx_video",
    inventory_function=inventory_lnx_video,
)
