#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="redundant-expr"

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Literal

import livestatus

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.watolib.groups_io import NothingOrChoices, PermittedPath
from cmk.inventory.structured_data import (
    filter_tree,
    HistoryArchivePath,
    HistoryDeltaPath,
    HistoryEntry,
    HistoryStore,
    ImmutableDeltaTree,
    ImmutableTree,
    InventoryStore,
    load_history,
    merge_trees,
    parse_from_raw_status_data_tree,
    parse_visible_raw_path,
    SDFilterChoice,
    SDKey,
    SDNodeName,
    SDPath,
)


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey = SDKey("")

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""


def _sanitize_path(path: Sequence[str]) -> SDPath:
    # ":": Nested tables, see also lib/structured_data.py
    return tuple(
        SDNodeName(p) for part in path for p in (part.split(":") if ":" in part else [part]) if p
    )


def parse_internal_raw_path(raw: str) -> InventoryPath:
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
#   - parse_internal_raw_path parses NOT visible, internal tree paths used in displayhints/views
#   - cmk.inventory.structured_data.py::parse_visible_raw_path
#     parses visible, internal tree paths for contact groups etc.
# => Should be unified one day.


def _transform_attribute[T](
    f: Callable[[str], T], x: NothingOrChoices | None
) -> Literal["nothing", "all"] | Sequence[T]:
    if x is None:
        return "all"
    if x == "nothing":
        return x
    return [f(y) for y in x[1]]  # choices


def _make_filter_choices_from_permitted_paths(
    permitted_paths: Sequence[PermittedPath],
) -> Sequence[SDFilterChoice]:
    return [
        SDFilterChoice(
            path=parse_visible_raw_path(entry["visible_raw_path"]),
            pairs=_transform_attribute(SDKey, entry.get("attributes")),
            columns=_transform_attribute(SDKey, entry.get("columns")),
            nodes=_transform_attribute(SDNodeName, entry.get("nodes")),
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

    return [
        _make_filter_choice(parse_internal_raw_path(raw_path)) for raw_path in api_request_paths
    ]


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

    inv_store = InventoryStore(cmk.utils.paths.omd_root)
    match tree_type:
        case "inventory":
            return inv_store.load_inventory_tree(host_name=host_name)
        case "status_data":
            return inv_store.load_status_data_tree(host_name=host_name)


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


def verify_permission(site_id: SiteId | None, host_name: HostName) -> None:
    if user.may("general.see_all"):
        return

    query = "GET hosts\nFilter: host_name = {}\nStats: state >= 0{}".format(
        livestatus.lqencode(host_name),
        "\nAuthUser: %s" % livestatus.lqencode(user.id) if user.id else "",
    )

    if site_id:
        sites.live().set_only_sites([site_id])

    try:
        result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    except livestatus.MKLivestatusNotFoundError:
        raise MKAuthException(
            _("No such inventory tree of host %s. You may also have no access to this host.")
            % host_name
        )
    finally:
        if site_id:
            sites.live().set_only_sites()

    if result[0] == 0:
        raise MKAuthException(_("You are not allowed to access the host %s.") % host_name)


def load_tree(*, host_name: HostName | None, raw_status_data_tree: bytes) -> ImmutableTree:
    """Load inventory tree from file, status data tree from row,
    merge these trees and returns the filtered tree"""
    inventory_tree = _load_tree_from_file(tree_type="inventory", host_name=host_name)
    status_data_tree = (
        parse_from_raw_status_data_tree(raw_status_data_tree)
        if raw_status_data_tree
        else _load_tree_from_file(tree_type="status_data", host_name=host_name)
    )

    merged_tree = merge_trees(inventory_tree, status_data_tree)
    if isinstance(permitted_paths := _get_permitted_inventory_paths(), list):
        return filter_tree(merged_tree, _make_filter_choices_from_permitted_paths(permitted_paths))

    return merged_tree


def get_raw_status_data_via_livestatus(site: SiteId | None, host_name: HostName) -> bytes:
    query = (
        "GET hosts\nColumns: host_structured_status\nFilter: host_name = %s\n"
        % livestatus.lqencode(host_name)
    )
    try:
        sites.live().set_only_sites([site] if site else None)
        result = sites.live().query(query)
    finally:
        sites.live().set_only_sites()

    if result and result[0]:
        return result[0][0]
    return b""


def inventory_of_host(
    site_id: SiteId | None, host_name: HostName, filters: Sequence[SDFilterChoice]
) -> ImmutableTree:
    verify_permission(site_id, host_name)
    tree = load_tree(
        host_name=host_name,
        raw_status_data_tree=get_raw_status_data_via_livestatus(site_id, host_name),
    )
    return filter_tree(tree, filters) if filters else tree


def load_latest_delta_tree(history_store: HistoryStore, hostname: HostName) -> ImmutableDeltaTree:
    if "/" in hostname:
        return ImmutableDeltaTree()

    history = load_history(
        history_store,
        hostname,
        history_paths_filter=lambda paths: [paths[-1]] if paths else [],
        delta_tree_filters=(
            _make_filter_choices_from_permitted_paths(permitted_paths)
            if isinstance(permitted_paths := _get_permitted_inventory_paths(), list)
            else None
        ),
    )
    return history.entries[0].delta_tree if history.entries else ImmutableDeltaTree()


def _sort_corrupted_history_files(
    archive_dir: Path, corrupted_history_files: Sequence[Path]
) -> Sequence[str]:
    return sorted([str(fp.relative_to(archive_dir.parent)) for fp in set(corrupted_history_files)])


def load_delta_tree(
    history_store: HistoryStore, hostname: HostName, timestamp: int
) -> tuple[ImmutableDeltaTree, Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    if "/" in hostname:
        return ImmutableDeltaTree(), []  # just for security reasons

    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.

    def _search_timestamps(
        paths: Sequence[HistoryDeltaPath | HistoryArchivePath], timestamp: int
    ) -> Sequence[HistoryDeltaPath | HistoryArchivePath]:
        for path in paths:
            if path.current_timestamp == timestamp:
                return [path]
        raise MKGeneralException(
            _("Found no history entry at the time of '%s' for the host '%s'")
            % (timestamp, hostname)
        )

    history = load_history(
        history_store,
        hostname,
        history_paths_filter=lambda paths: _search_timestamps(paths, timestamp),
        delta_tree_filters=(
            _make_filter_choices_from_permitted_paths(permitted_paths)
            if isinstance(permitted_paths := _get_permitted_inventory_paths(), list)
            else None
        ),
    )
    return (
        history.entries[0].delta_tree if history.entries else ImmutableDeltaTree(),
        _sort_corrupted_history_files(history_store.inv_paths.archive_dir, history.corrupted),
    )


def get_history(
    history_store: HistoryStore, hostname: HostName
) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    history = load_history(
        history_store,
        hostname,
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=(
            _make_filter_choices_from_permitted_paths(permitted_paths)
            if isinstance(permitted_paths := _get_permitted_inventory_paths(), list)
            else None
        ),
    )
    return history.entries, _sort_corrupted_history_files(
        history_store.inv_paths.archive_dir, history.corrupted
    )
