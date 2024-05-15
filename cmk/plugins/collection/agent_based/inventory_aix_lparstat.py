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


def parse_aix_lparstat_inventory(string_table: StringTable) -> Section:
    lines = (raw[0] for raw in string_table if ":" in raw[0])
    pairs = (line.split(":", 1) for line in lines)
    parsed = {k.strip(): v.strip() for k, v in pairs}
    return parsed


agent_section_aix_lparstat_inventory = AgentSection(
    name="aix_lparstat_inventory",
    parse_function=parse_aix_lparstat_inventory,
)


def inventory_aix_lparstat_inventory(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes={
            k: v
            for k, pk in (
                ("cpu_max_capa", "Maximum Capacity"),
                ("type", "Type"),
            )
            if (v := section[pk]) is not None
        },
    )
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            k: v
            for k, pk in (
                ("node_name", "Node Name"),
                ("partition_name", "Partition Name"),
                ("partition_number", "Partition Number"),
            )
            if (v := section[pk]) is not None
        },
    )


inventory_plugin_aix_lparstat_inventory = InventoryPlugin(
    name="aix_lparstat_inventory",
    inventory_function=inventory_aix_lparstat_inventory,
)
