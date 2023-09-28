#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.citrix_controller import parse_citrix_controller, Section

register.agent_section(
    name="citrix_controller",
    parse_function=parse_citrix_controller,
)


def inventory_citrix_controller(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "citrix", "controller"],
        inventory_attributes={
            "controller_version": section.version,
        },
    )


register.inventory_plugin(
    name="citrix_controller",
    inventory_function=inventory_citrix_controller,
)
