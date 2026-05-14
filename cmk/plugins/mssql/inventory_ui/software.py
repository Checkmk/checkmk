#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.inventory_ui.v1_unstable import (
    Alignment,
    BackgroundColor,
    BoolField,
    LabelColor,
    Node,
    Table,
    TextField,
    Title,
)


def _style_mssql_is_clustered(
    value: bool,
) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    if value:
        yield LabelColor.BLACK
        yield BackgroundColor.GREEN
    else:
        yield LabelColor.WHITE
        yield BackgroundColor.DARK_GRAY


node_software_applications_mssql = Node(
    name="software_applications_mssql",
    path=["software", "applications", "mssql"],
    title=Title("MSSQL"),
)

node_software_applications_mssql_instances = Node(
    name="software_applications_mssql_instances",
    path=["software", "applications", "mssql", "instances"],
    title=Title("Instances"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "product": TextField(Title("Product")),
            "edition": TextField(Title("Edition")),
            "version": TextField(Title("Version")),
            "clustered": BoolField(Title("Clustered"), style=_style_mssql_is_clustered),
            "cluster_name": TextField(Title("Cluster name")),
            "active_node": TextField(Title("Active node")),
            "node_names": TextField(Title("Node names")),
        },
    ),
)
