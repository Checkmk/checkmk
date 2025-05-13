#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils.paths
from cmk.utils.structured_data import (
    ImmutableDeltaTree,
    ImmutableTree,
    InventoryStore,
    SDPath,
)

from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.inventory import get_raw_status_data_via_livestatus, load_latest_delta_tree, load_tree
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.type_defs import (
    HTTPVariables,
    PermittedViewSpecs,
    Rows,
    SingleInfos,
    Visual,
    VisualContext,
)
from cmk.gui.valuespec import Hostname
from cmk.gui.views.store import get_permitted_views
from cmk.gui.visuals.type import VisualType


class VisualTypeViews(VisualType):
    """Register the views as a visual type"""

    @property
    def ident(self) -> str:
        return "views"

    @property
    def title(self) -> str:
        return _("view")

    @property
    def plural_title(self) -> str:
        return _("views")

    @property
    def ident_attr(self) -> str:
        return "view_name"

    @property
    def multicontext_links(self) -> bool:
        return False

    @property
    def show_url(self) -> str:
        return "view.py"

    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        return iter(())

    def add_visual_handler(
        self,
        target_visual_name: str,
        add_type: str,
        context: VisualContext | None,
        parameters: dict,
    ) -> None:
        return None

    def load_handler(self) -> None:
        pass

    @property
    def permitted_visuals(self) -> PermittedViewSpecs:
        return get_permitted_views()

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
        result = super().link_from(
            linking_view_single_infos, linking_view_rows, visual, context_vars
        )
        if result is False:
            return False

        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

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
        return _has_inventory_tree(
            hostname,
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree"),
            is_history=False,
        ) or _has_inventory_tree(
            hostname,
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree_history"),
            is_history=True,
        )


def _has_inventory_tree(
    hostname: HostName,
    site_id: SiteId,
    path: SDPath | None,
    is_history: bool,
) -> bool:
    if path is None:
        return False

    # FIXME In order to decide whether this view is enabled
    # do we really need to load the whole tree?
    try:
        inventory_tree = _get_inventory_tree(is_history, hostname, site_id)
    except Exception as e:
        if active_config.debug:
            html.show_warning("%s" % e)
        return False

    return bool(inventory_tree.get_tree(path))


def _get_inventory_tree(
    is_history: bool, host_name: HostName, site_id: SiteId
) -> ImmutableTree | ImmutableDeltaTree:
    tree_cache = g.setdefault("inventory_tree_cache", {})

    cache_id = (is_history, host_name, site_id)
    if cache_id in tree_cache:
        return tree_cache[cache_id]

    tree: ImmutableTree | ImmutableDeltaTree = (
        load_latest_delta_tree(InventoryStore(cmk.utils.paths.omd_root), host_name)
        if is_history
        else load_tree(
            host_name=host_name,
            raw_status_data_tree=get_raw_status_data_via_livestatus(site_id, host_name),
        )
    )
    tree_cache[cache_id] = tree
    return tree
