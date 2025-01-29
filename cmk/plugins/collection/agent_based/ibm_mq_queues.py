#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.lib.ibm_mq import parse_ibm_mq

Section = Mapping[str, Any]


def parse_ibm_mq_queues(string_table: StringTable) -> Section:
    return parse_ibm_mq(string_table, "QUEUE")


agent_section_ibm_mq_queues = AgentSection(
    name="ibm_mq_queues",
    parse_function=parse_ibm_mq_queues,
)


def inventory_ibm_mq_queues(section: Section) -> InventoryResult:
    for item, attrs in sorted(section.items(), key=lambda t: t[0]):
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, qname = item.split(":")
        yield TableRow(
            path=["software", "applications", "ibm_mq", "queues"],
            key_columns={
                "qmgr": qmname,
                "name": qname,
            },
            inventory_columns={
                "maxdepth": attrs["MAXDEPTH"],
                "maxmsgl": attrs.get("MAXMSGL", "n/a"),
                "created": (
                    "{} {}".format(
                        attrs.get("CRDATE", "n/a"), attrs.get("CRTIME", "").replace(".", ":")
                    )
                ).strip(),
                "altered": (
                    "{} {}".format(
                        attrs.get("ALTDATE", "n/a"), attrs.get("ALTTIME", "").replace(".", ":")
                    )
                ).strip(),
                "monq": attrs.get("MONQ", "n/a"),
            },
            status_columns={},
        )


inventory_plugin_ibm_mq_queues = InventoryPlugin(
    name="ibm_mq_queues",
    inventory_function=inventory_ibm_mq_queues,
)
