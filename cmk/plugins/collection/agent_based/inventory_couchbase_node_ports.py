#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.lib import couchbase

agent_section_couchbase_nodes_ports = AgentSection(
    name="couchbase_nodes_ports",
    parse_function=couchbase.parse_couchbase_lines,
)


def _get_path(name: str) -> list[str]:
    node = name.replace(".", "-").replace(":", "-")
    return ["software", "applications", "couchbase", "nodes", node, "ports"]


def inventory_couchbase_nodes_ports(section: couchbase.Section) -> InventoryResult:
    yield from (
        Attributes(
            path=_get_path(name),
            inventory_attributes=data.get("ports", {}),
        )
        for name, data in section.items()
    )


inventory_plugin_couchbase_nodes_ports = InventoryPlugin(
    name="couchbase_nodes_ports",
    inventory_function=inventory_couchbase_nodes_ports,
)
