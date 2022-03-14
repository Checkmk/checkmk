#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.ibm_mq import parse_ibm_mq

Section = Mapping[str, Any]


def parse_ibm_mq_channels(string_table: StringTable) -> Section:
    return parse_ibm_mq(string_table, "CHANNEL")


register.agent_section(
    name="ibm_mq_channels",
    parse_function=parse_ibm_mq_channels,
)


def inventory_ibm_mq_channels(section: Section) -> InventoryResult:
    path = ["software", "applications", "ibm_mq", "channels"]
    for item, attrs in section.items():
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, cname = item.split(":")
        yield TableRow(
            path=path,
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


register.inventory_plugin(
    name="ibm_mq_channels",
    inventory_function=inventory_ibm_mq_channels,
)
