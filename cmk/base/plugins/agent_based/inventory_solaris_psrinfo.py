#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 8 virtual processors (0-7)
#  SPARC64-VII+ (portid 1024 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (8-15)
#  SPARC64-VII+ (portid 1032 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (16-23)
#  SPARC64-VII+ (portid 1040 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (24-31)
#  SPARC64-VII+ (portid 1048 impl 0x7 ver 0xc1 clock 2660 MHz)

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 10 cores and 80 virtual processors (0-79)
#  The core has 8 virtual processors (0-7)
#  The core has 8 virtual processors (8-15)
#  The core has 8 virtual processors (16-23)
#  The core has 8 virtual processors (24-31)
#  The core has 8 virtual processors (32-39)
#  The core has 8 virtual processors (40-47)
#  The core has 8 virtual processors (48-55)
#  The core has 8 virtual processors (56-63)
#  The core has 8 virtual processors (64-71)
#  The core has 8 virtual processors (72-79)
#    SPARC-T5 (chipid 0, clock 3600 MHz)

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 8 virtual processors (0-7)
#  SPARC-T5 (chipid 0, clock 3600 MHz)

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


def inventory_solaris_psrinfo(section: StringTable) -> InventoryResult:
    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes={
            "Model": section[-1][0],
            "Maximum Speed": f"{section[-1][-2]} {section[-1][-1].strip(')')}",
        },
    )


register.inventory_plugin(
    name="solaris_psrinfo",
    inventory_function=inventory_solaris_psrinfo,
)
