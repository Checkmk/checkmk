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


def parse_ibm_mq_queues(string_table: StringTable) -> Section:
    return parse_ibm_mq(string_table, "QUEUE")


register.agent_section(
    name="ibm_mq_queues",
    parse_function=parse_ibm_mq_queues,
)


def inventory_ibm_mq_queues(section: Section) -> InventoryResult:
    path = ["software", "applications", "ibm_mq", "queues"]
    for item, attrs in sorted(section.items(), key=lambda t: t[0]):
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, qname = item.split(":")
        yield TableRow(
            path=path,
            key_columns={
                "qmgr": qmname,
                "name": qname,
            },
            inventory_columns={
                "maxdepth": attrs["MAXDEPTH"],
                "maxmsgl": attrs.get("MAXMSGL", "n/a"),
                "created": (
                    "%s %s"
                    % (attrs.get("CRDATE", "n/a"), attrs.get("CRTIME", "").replace(".", ":"))
                ).strip(),
                "altered": (
                    "%s %s"
                    % (attrs.get("ALTDATE", "n/a"), attrs.get("ALTTIME", "").replace(".", ":"))
                ).strip(),
                "monq": attrs.get("MONQ", "n/a"),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="ibm_mq_queues",
    inventory_function=inventory_ibm_mq_queues,
)
