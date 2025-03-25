#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Literal

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    deserialize_tree,
    ImmutableTree,
    load_tree,
    parse_visible_raw_path,
    SDFilterChoice,
    SDKey,
    SDNodeName,
    SDPath,
)

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row
from cmk.gui.watolib.groups_io import PermittedPath


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


def _sanitize_path(path: Sequence[str]) -> SDPath:
    # ":": Nested tables, see also lib/structured_data.py
    return tuple(
        SDNodeName(p) for part in path for p in (part.split(":") if ":" in part else [part]) if p
    )


def parse_inventory_path(raw: str) -> InventoryPath:
    if not raw:
        return InventoryPath(
            path=tuple(),
            source=TreeSource.node,
        )
    if raw.endswith("."):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.node,
        )
    if raw.endswith(":"):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.table,
        )
    path = raw.strip(".").split(".")
    sanitized_path = _sanitize_path(path[:-1])
    if ":" in path[-2]:
        source = TreeSource.table
        # Forget the last '*' or an index like '17'
        # because it's related to columns (not nodes)
        sanitized_path = sanitized_path[:-1]
    else:
        source = TreeSource.attributes
    return InventoryPath(
        path=sanitized_path,
        source=source,
        key=SDKey(path[-1]),
    )


# TODO Cleanup variation:
#   - parse_inventory_path parses NOT visible, internal tree paths used in displayhints/views
#   - cmk.utils.structured_data.py::parse_visible_raw_path
#     parses visible, internal tree paths for contact groups etc.
# => Should be unified one day.


def make_filter_choices_from_permitted_paths(
    permitted_paths: Sequence[PermittedPath],
) -> Sequence[SDFilterChoice]:
    return [
        SDFilterChoice(
            path=parse_visible_raw_path(entry["visible_raw_path"]),
            pairs=(
                [SDKey(a) for a in attributes[-1]]
                if isinstance(attributes := entry.get("attributes", "all"), tuple)
                else attributes
            ),
            columns=(
                [SDKey(c) for c in columns[-1]]
                if isinstance(columns := entry.get("columns", "all"), tuple)
                else columns
            ),
            nodes=(
                [SDNodeName(n) for n in nodes[-1]]
                if isinstance(nodes := entry.get("nodes", "all"), tuple)
                else nodes
            ),
        )
        for entry in permitted_paths
        if entry
    ]


def make_filter_choices_from_api_request_paths(
    api_request_paths: Sequence[str],
) -> Sequence[SDFilterChoice]:
    def _make_filter_choice(inventory_path: InventoryPath) -> SDFilterChoice:
        if inventory_path.key:
            return SDFilterChoice(
                path=inventory_path.path,
                pairs=[inventory_path.key],
                columns=[inventory_path.key],
                nodes="nothing",
            )
        return SDFilterChoice(
            path=inventory_path.path,
            pairs="all",
            columns="all",
            nodes="all",
        )

    return [_make_filter_choice(parse_inventory_path(raw_path)) for raw_path in api_request_paths]


@request_memoize(maxsize=None)
def _load_tree_from_file(
    *, tree_type: Literal["inventory", "status_data"], host_name: HostName | None
) -> ImmutableTree:
    """Load data of a host, cache it in the current HTTP request"""
    if not host_name:
        return ImmutableTree()
    if "/" in host_name:
        # just for security reasons
        return ImmutableTree()
    return load_tree(
        Path(
            cmk.utils.paths.inventory_output_dir
            if tree_type == "inventory"
            else cmk.utils.paths.status_data_dir
        )
        / host_name
    )


@request_memoize()
def _get_permitted_inventory_paths() -> Sequence[PermittedPath] | None:
    """
    Returns either a list of permitted paths or
    None in case the user is allowed to see the whole tree.
    """

    user_groups = [] if user.id is None else userdb.contactgroups_of_user(user.id)

    if not user_groups:
        return None

    forbid_whole_tree = False
    permitted_paths = []
    for user_group in user_groups:
        inventory_paths = active_config.multisite_contactgroups.get(user_group, {}).get(
            "inventory_paths"
        )
        if inventory_paths is None:
            # Old configuration: no paths configured means 'allow_all'
            return None

        if inventory_paths == "allow_all":
            return None

        if inventory_paths == "forbid_all":
            forbid_whole_tree = True
            continue

        permitted_paths.extend(inventory_paths[1])

    if forbid_whole_tree and not permitted_paths:
        return []

    return permitted_paths


def load_filtered_and_merged_tree(row: Row) -> ImmutableTree:
    """Load inventory tree from file, status data tree from row,
    merge these trees and returns the filtered tree"""
    host_name = row.get("host_name")
    inventory_tree = _load_tree_from_file(tree_type="inventory", host_name=host_name)
    if raw_status_data_tree := row.get("host_structured_status"):
        status_data_tree = deserialize_tree(ast.literal_eval(raw_status_data_tree.decode("utf-8")))
    else:
        status_data_tree = _load_tree_from_file(tree_type="status_data", host_name=host_name)

    merged_tree = inventory_tree.merge(status_data_tree)
    if isinstance(permitted_paths := _get_permitted_inventory_paths(), list):
        return merged_tree.filter(make_filter_choices_from_permitted_paths(permitted_paths))

    return merged_tree


def get_short_inventory_filepath(hostname: HostName) -> Path:
    return (
        Path(cmk.utils.paths.inventory_output_dir)
        .joinpath(hostname)
        .relative_to(cmk.utils.paths.omd_root)
    )


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey = SDKey("")

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""
