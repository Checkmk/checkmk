#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.lib.citrix_controller import parse_citrix_controller, Section

agent_section_citrix_controller = AgentSection(
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


inventory_plugin_citrix_controller = InventoryPlugin(
    name="citrix_controller",
    inventory_function=inventory_citrix_controller,
)
