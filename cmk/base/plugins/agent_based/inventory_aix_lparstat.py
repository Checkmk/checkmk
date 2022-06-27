#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, str]


def parse_aix_lparstat_inventory(string_table: StringTable) -> Section:
    lines = (raw[0] for raw in string_table if ":" in raw[0])
    pairs = (line.split(":", 1) for line in lines)
    parsed = {k.strip(): v.strip() for k, v in pairs}
    return parsed


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


register.inventory_plugin(
    name="aix_lparstat_inventory",
    inventory_function=inventory_aix_lparstat_inventory,
)
