#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, Optional

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Version = NewType("Version", str)


def parse_citrix_controller(string_table: StringTable) -> Optional[Version]:
    for line in string_table:
        if line[0] == "ControllerVersion":
            return Version(line[1])
    return None


register.agent_section(
    name="citrix_controller",
    parse_function=parse_citrix_controller,
)


def inventory_citrix_controller(section: Version) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "citrix", "controller"],
        inventory_attributes={
            "controller_version": section,
        },
    )


register.inventory_plugin(
    name="citrix_controller",
    inventory_function=inventory_citrix_controller,
)
