#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

import cmk.livestatus_client as livestatus
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
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.filtering import filter_tree, SDFilterChoice
from cmk.inventory.history import HistoryEntry, HistoryStore
from cmk.inventory.store import InventoryStore
from cmk.inventory.trees import ImmutableTree, parse_visible_raw_path, SDKey, SDNodeName


def _transform_attribute[T](
    f: Callable[[str], T], x: NothingOrChoices | None
) -> Literal["nothing", "all"] | Sequence[T]:
    if x is None:
        return "all"
    if x == "nothing":
        return x
    return [f(y) for y in x[1]]  # choices


def make_filter_choices_from_permitted_paths(
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
        if entry.get("visible_raw_path")
    ]


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


def _permitted_filter_choices() -> Sequence[SDFilterChoice] | None:
    return (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := _get_permitted_inventory_paths(), list)
        else None
    )


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
            _(
                "No such inventory tree of host %(host_name)s. You may also have no access to this host."
            )
            % {"host_name": host_name}
        )
    finally:
        if site_id:
            sites.live().set_only_sites()

    if result[0] == 0:
        raise MKAuthException(
            _("You are not allowed to access the host %(host_name)s.") % {"host_name": host_name}
        )


@request_memoize(maxsize=None)
def load_tree(*, host_name: HostName | None, raw_status_data_tree: bytes) -> ImmutableTree:
    if not host_name:
        return ImmutableTree()

    merged_tree = InventoryStore(cmk.utils.paths.omd_root).load_merged_tree(
        host_name=host_name, raw_status_data_tree=raw_status_data_tree
    )
    if (filters := _permitted_filter_choices()) is not None:
        return filter_tree(merged_tree, filters)

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

    if result and result[0] and isinstance(raw_status_data := result[0][0], bytes):
        return raw_status_data
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
    history = history_store.load_latest(hostname, delta_tree_filters=_permitted_filter_choices())
    return history.entries[0].delta_tree if history.entries else ImmutableDeltaTree()


def _sort_corrupted_history_files(
    archive_dir: Path, corrupted_history_files: Sequence[Path]
) -> Sequence[str]:
    return sorted([str(fp.relative_to(archive_dir.parent)) for fp in set(corrupted_history_files)])


def load_delta_tree(
    history_store: HistoryStore, hostname: HostName, timestamp: int
) -> tuple[ImmutableDeltaTree, Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    history = history_store.load_at(
        hostname, timestamp, delta_tree_filters=_permitted_filter_choices()
    )
    if history is None:
        raise MKGeneralException(
            _("Found no history entry at the time of '%(timestamp)s' for the host '%(hostname)s'")
            % {"timestamp": timestamp, "hostname": hostname}
        )
    return (
        history.entries[0].delta_tree if history.entries else ImmutableDeltaTree(),
        _sort_corrupted_history_files(history_store.inv_paths.archive_dir, history.corrupted),
    )


def get_history(
    history_store: HistoryStore, hostname: HostName
) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    history = history_store.load(hostname, delta_tree_filters=_permitted_filter_choices())
    return history.entries, _sort_corrupted_history_files(
        history_store.inv_paths.archive_dir, history.corrupted
    )
