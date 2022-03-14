#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

import re
from typing import Mapping

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, str]


def parse_lnx_video(string_table: StringTable) -> Section:
    array = {}
    for line in string_table:
        if len(line) > 1:
            if re.search("VGA compatible controller", line[1]):
                array["name"] = line[2]
            elif line[0] == "Subsystem":
                array["subsystem"] = line[1]
            elif line[0] == "Kernel driver in use":
                array["driver"] = line[1]
    return array


register.agent_section(
    name="lnx_video",
    parse_function=parse_lnx_video,
)


def inventory_lnx_video(section: Section) -> InventoryResult:
    # FIXME This is very strange: Raw data is parsed into ONE dict,
    # but we save the controller attributes in a table...
    # Maybe there are more controllers?
    path = ["hardware", "video"]
    if "name" in section:
        yield TableRow(
            path=path,
            key_columns={
                "name": section["name"],
            },
            inventory_columns={
                "subsystem": section.get("subsystem"),
                "driver": section.get("driver"),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="lnx_video",
    inventory_function=inventory_lnx_video,
)
