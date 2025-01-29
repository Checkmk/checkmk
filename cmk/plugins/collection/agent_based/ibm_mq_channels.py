#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.lib.ibm_mq import parse_ibm_mq

Section = Mapping[str, Any]


def parse_ibm_mq_channels(string_table: StringTable) -> Section:
    return parse_ibm_mq(string_table, "CHANNEL")


agent_section_ibm_mq_channels = AgentSection(
    name="ibm_mq_channels",
    parse_function=parse_ibm_mq_channels,
)


def inventory_ibm_mq_channels(section: Section) -> InventoryResult:
    for item, attrs in section.items():
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, cname = item.split(":")
        yield TableRow(
            path=["software", "applications", "ibm_mq", "channels"],
            key_columns={
                "qmgr": qmname,
                "name": cname,
            },
            inventory_columns={
                "type": attrs.get("CHLTYPE", "Unknown"),
                "monchl": attrs.get("MONCHL", "n/a"),
            },
            status_columns={
                "status": attrs.get("STATUS", "Unknown"),
            },
        )


inventory_plugin_ibm_mq_channels = InventoryPlugin(
    name="ibm_mq_channels",
    inventory_function=inventory_ibm_mq_channels,
)
