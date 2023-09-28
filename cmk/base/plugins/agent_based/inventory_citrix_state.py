#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.utils.citrix_state import parse_citrix_state, Section

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult

register.agent_section(
    name="citrix_state",
    parse_function=parse_citrix_state,
)


def inventory_citrix_state(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "citrix", "vm"],
        inventory_attributes={
            k: v
            for k, kp in (
                ("desktop_group_name", "DesktopGroupName"),
                ("catalog", "Catalog"),
                ("agent_version", "AgentVersion"),
            )
            if (v := section["instance"].get(kp)) is not None
        },
    )


register.inventory_plugin(
    name="citrix_state",
    inventory_function=inventory_citrix_state,
)
