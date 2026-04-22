#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Iterator
from typing import override

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.inventory import get_raw_status_data_via_livestatus, load_latest_delta_tree, load_tree
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.type_defs import (
    AllViewSpecs,
    HTTPVariables,
    PermittedViewSpecs,
    Rows,
    SingleInfos,
    Visual,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import Hostname
from cmk.gui.views.store import get_all_views, get_permitted_views
from cmk.gui.visuals.type import VisualType
from cmk.inventory.structured_data import (
    HistoryStore,
    ImmutableDeltaTree,
    ImmutableTree,
    SDPath,
)

_InventoryTreeCache = dict[tuple[bool, HostName, SiteId], ImmutableTree | ImmutableDeltaTree]


class VisualTypeViews(VisualType):
    """Register the views as a visual type"""

    @property
    @override
    def ident(self) -> str:
        return "views"

    @property
    @override
    def title(self) -> str:
        return _("view")

    @property
    @override
    def plural_title(self) -> str:
        return _("views")

    @property
    @override
    def ident_attr(self) -> str:
        return "view_name"

    @property
    @override
    def multicontext_links(self) -> bool:
        return False

    @property
    @override
    def show_url(self) -> str:
        return "view.py"

    @override
    def page_menu_add_to_entries(
        self, add_type: str, user_permissions: UserPermissions
    ) -> Iterator[PageMenuEntry]:
        return iter(())

    @override
    def add_visual_handler(
        self,
        request: Request,
        target_visual_name: str,
        add_type: str,
        context: VisualContext | None,
        parameters: dict,
        user_permissions: UserPermissions,
    ) -> None:
        return None

    @override
    def visuals(self) -> AllViewSpecs:
        return get_all_views()

    @override
    def permitted_visuals(
        self, visuals: AllViewSpecs, user_permissions: UserPermissions
    ) -> PermittedViewSpecs:
        return get_permitted_views()

    @override
    def link_from(
        self,
        linking_view_single_infos: SingleInfos,
        linking_view_rows: Rows,
        visual: Visual,
        context_vars: HTTPVariables,
    ) -> bool:
        """This has been implemented for HW/SW Inventory views which are often useless when a host
        has no such information available. For example the "Oracle Tablespaces" inventory view is
        useless on hosts that don't host Oracle databases."""
        tree_cache: _InventoryTreeCache = g.setdefault("inventory_tree_cache", {})

        def has_inventory_tree(
            hostname: HostName, site_id: SiteId, path: SDPath | None, is_history: bool
        ) -> bool:
            return _has_inventory_tree(hostname, site_id, path, is_history, tree_cache)

        return _compute_link_from_result(
            linking_view_single_infos,
            linking_view_rows,
            visual,
            context_vars,
            base_link_from=super().link_from,
            has_inventory_tree=has_inventory_tree,
        )


def _has_inventory_tree(
    hostname: HostName,
    site_id: SiteId,
    path: SDPath | None,
    is_history: bool,
    tree_cache: _InventoryTreeCache,
) -> bool:
    if path is None:
        return False

    # FIXME In order to decide whether this view is enabled
    # do we really need to load the whole tree?
    try:
        inventory_tree = _get_inventory_tree(is_history, hostname, site_id, tree_cache)
    except Exception as e:
        if active_config.debug:
            html.show_warning("%s" % e)
        return False

    return bool(inventory_tree.get_tree(path))


def _get_inventory_tree(
    is_history: bool,
    hostname: HostName,
    site_id: SiteId,
    tree_cache: _InventoryTreeCache,
) -> ImmutableTree | ImmutableDeltaTree:
    cache_id = (is_history, hostname, site_id)
    if cache_id in tree_cache:
        return tree_cache[cache_id]

    tree: ImmutableTree | ImmutableDeltaTree = (
        load_latest_delta_tree(HistoryStore(cmk.utils.paths.omd_root), hostname)
        if is_history
        else load_tree(
            host_name=hostname,
            raw_status_data_tree=get_raw_status_data_via_livestatus(site_id, hostname),
        )
    )
    tree_cache[cache_id] = tree
    return tree


def _compute_link_from_result(
    linking_view_single_infos: SingleInfos,
    linking_view_rows: Rows,
    visual: Visual,
    context_vars: HTTPVariables,
    base_link_from: Callable[[SingleInfos, Rows, Visual, HTTPVariables], bool],
    has_inventory_tree: Callable[[HostName, SiteId, SDPath | None, bool], bool],
) -> bool:
    link_from = visual["link_from"]
    if not link_from:
        return True  # No link from filtering: Always display this.

    if "has_inventory_tree" not in link_from and "has_inventory_tree_history" not in link_from:
        # No inventory checks — delegate fully to base class.
        return base_link_from(linking_view_single_infos, linking_view_rows, visual, context_vars)

    # Inventory checks use context_vars directly and do not need row data. The base class
    # returns False for empty rows, which would wrongly suppress inventory links on views
    # whose datasource yields no rows (e.g. "Services of host" for a host with no services).
    # Only the single_infos guard from the base class is still relevant here.
    single_info_condition = link_from.get("single_infos")
    if single_info_condition and not set(single_info_condition).issubset(linking_view_single_infos):
        return False

    # Non-inventory conditions (e.g. host_labels) must still be evaluated via the base class.
    # We call it after the single_infos guard so a mismatch short-circuits before the base
    # class can raise NotImplementedError for unsupported single_infos combinations.
    _inventory_keys = {"has_inventory_tree", "has_inventory_tree_history", "single_infos"}
    if link_from.keys() - _inventory_keys:
        if not base_link_from(linking_view_single_infos, linking_view_rows, visual, context_vars):
            return False

    context = dict(context_vars)
    if (hostname := context.get("host")) is None:
        # No host data? Keep old behaviour
        return True

    if hostname == "":
        return False

    if isinstance(hostname, int):
        return False

    # TODO: host is not correctly validated by visuals. Do it here for the moment.
    try:
        Hostname().validate_value(hostname, "")
    except MKUserError:
        return False

    if not (site_id := context.get("site")):
        return False

    hostname = HostName(hostname)
    return has_inventory_tree(
        hostname,
        SiteId(str(site_id)),
        link_from.get("has_inventory_tree"),
        False,
    ) or has_inventory_tree(
        hostname,
        SiteId(str(site_id)),
        link_from.get("has_inventory_tree_history"),
        True,
    )
