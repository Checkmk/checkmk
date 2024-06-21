#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mssql_clusters>>>
# MSSQL_VIM_SQLEXP node1 node1,node2

from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow


class DBInstance(NamedTuple):
    instance_id: str
    active_node: str
    nodes: Sequence[str]


Section = Sequence[DBInstance]


def parse_mssql_clusters(string_table: StringTable) -> Section:
    instances = []
    for line in string_table:
        if len(line) == 4:
            inst = DBInstance(
                instance_id=line[0],
                active_node=line[2],
                nodes=line[3].split(","),
            )
        elif len(line) == 3:
            # DB name may be ''
            inst = DBInstance(
                instance_id=line[0],
                active_node=line[1],
                nodes=line[2].split(","),
            )
        else:
            continue

        instances.append(inst)
    return instances


agent_section_mssql_clusters = AgentSection(
    name="mssql_clusters",
    parse_function=parse_mssql_clusters,
)


def inventory_mssql_clusters(section: Section) -> InventoryResult:
    for inst in section:
        yield TableRow(
            path=["software", "applications", "mssql", "instances"],
            key_columns={
                "name": inst.instance_id,
            },
            inventory_columns={
                "active_node": inst.active_node,
                "node_names": ", ".join(inst.nodes),
            },
            status_columns={},
        )


inventory_plugin_mssql_clusters = InventoryPlugin(
    name="mssql_clusters",
    inventory_function=inventory_mssql_clusters,
)
