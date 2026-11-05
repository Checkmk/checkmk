#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence

import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.user_errors import user_errors
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.filtering import (
    filter_tree,
    make_filter_choices_from_contact_groups,
    SDFilterChoice,
)
from cmk.inventory.history import HistoryEntry, HistoryStore, sort_corrupted_history_files
from cmk.inventory.store import InventoryStore
from cmk.inventory.trees import ImmutableTree


@request_memoize()
def _permitted_filter_choices() -> Sequence[SDFilterChoice] | None:
    return make_filter_choices_from_contact_groups(
        [
            active_config.multisite_contactgroups.get(group, {}).get("inventory_paths")
            for group in ([] if user.id is None else userdb.contactgroups_of_user(user.id))
        ]
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
def load_tree(*, host_name: HostName, raw_status_data_tree: bytes) -> ImmutableTree:
    if not host_name:
        return ImmutableTree()

    merged_tree = InventoryStore(cmk.utils.paths.omd_root).load_merged_tree(
        host_name=host_name, raw_status_data_tree=raw_status_data_tree
    )
    if (filters := _permitted_filter_choices()) is not None:
        return filter_tree(merged_tree, filters)

    return merged_tree


def load_tree_of_host(
    *, raw_host_name: str, raw_status_data_tree: bytes, debug: bool
) -> ImmutableTree | None:
    try:
        return load_tree(
            host_name=HostName(raw_host_name), raw_status_data_tree=raw_status_data_tree
        )
    except Exception as e:
        if debug:
            html.show_warning("%s" % e)
        return None


def report_corrupted_trees(raw_host_names: Iterable[str]) -> None:
    user_errors.add(
        MKUserError(
            "load_inventory_tree",
            _(
                "Cannot load HW/SW inventory of %(hosts)s. Please remove the corrupted inventory or status data tree files."
            )
            % {"hosts": ", ".join(sorted(raw_host_names))},
        )
    )


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
        sort_corrupted_history_files(history_store.inv_paths.archive_dir, history.corrupted),
    )


def get_history(
    history_store: HistoryStore, hostname: HostName
) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    history = history_store.load(hostname, delta_tree_filters=_permitted_filter_choices())
    return history.entries, sort_corrupted_history_files(
        history_store.inv_paths.archive_dir, history.corrupted
    )
