#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import ImmutableTree

from cmk.gui.openapi.framework import QueryParam
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href

from .._tree import inventory_of_host


@dataclass(kw_only=True, slots=True)
class Attributes:
    pairs: dict[str, int | float | str | bool | None] = api_field(description="Key-value pairs")


@dataclass(kw_only=True, slots=True)
class Table:
    key_columns: Sequence[str] = api_field(
        description="The key columns which are used to identify a row"
    )
    rows: Sequence[Mapping[str, int | float | str | bool | None]] = api_field(
        description="The rows of an inventory table whereas each row consists of key-value pairs"
    )


@dataclass(kw_only=True, slots=True)
class Tree:
    attributes: "Attributes" = api_field(description="A collection of key-value pairs")
    table: "Table" = api_field(description="A collection of rows")
    nodes: Mapping[str, "Tree"] = api_field(description="Sub trees identified by node names")


def _transform_inventory_tree(tree: ImmutableTree) -> Tree:
    return Tree(
        attributes=Attributes(
            pairs={str(k): v for k, v in tree.attributes.pairs.items()},
        ),
        table=Table(
            key_columns=[str(kc) for kc in tree.table.key_columns],
            rows=[{str(k): v for k, v in r.items()} for r in tree.table.rows_by_ident.values()],
        ),
        nodes={
            node_name: _transform_inventory_tree(node)
            for node_name, node in tree.nodes_by_name.items()
        },
    )


@dataclass(kw_only=True, slots=True)
class HostInventoryTree:
    host_name: str = api_field(
        description="The HW/SW Inventory tree of the host",
    )
    inventory_tree: Tree = api_field(
        description="The HW/SW Inventory tree of the host",
    )


@dataclass(kw_only=True, slots=True)
class InventoryTreesCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["inventory"] = api_field(
        description="The domain type of the objects in the collection",
        example="inventory",
    )
    value: list[HostInventoryTree] = api_field(
        description="The HW/SW Inventory trees of hosts",
        example=[
            {
                "host_name": "hostname",
                "inventory_tree": {
                    "attributes": {"pairs": {"key": "value"}},
                    "table": {
                        "key_columns": ["column1"],
                        "rows": [{"column1": "value1", "column2": "value2"}],
                    },
                    "nodes": {
                        "nodename": {
                            "attributes": {"pairs": {"key": "value"}},
                            "table": {
                                "key_columns": ["column1"],
                                "rows": [{"column1": "value1", "column2": "value2"}],
                            },
                            "nodes": {},
                        }
                    },
                },
            }
        ],
    )


def get_inventory_trees(
    host_names: Annotated[
        list[str],
        QueryParam(
            description="List of host names",
            example="hostname",
            is_list=True,
        ),
    ],
) -> InventoryTreesCollectionModel:
    """Get the HW/SW Inventory trees of given hosts."""
    return InventoryTreesCollectionModel(
        id="inventory_trees",
        domainType="inventory",
        value=[
            HostInventoryTree(host_name=h, inventory_tree=_transform_inventory_tree(tree))
            for h in host_names
            if (tree := inventory_of_host(None, HostName(h), []))
        ],
        links=[LinkModel.create("self", collection_href("inventory"))],
    )
