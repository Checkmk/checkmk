#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence

from livestatus import SiteId

from cmk.utils.structured_data import SDPath, StructuredDataNode
from cmk.utils.type_defs import HostName

from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.inventory import (
    get_status_data_via_livestatus,
    load_filtered_and_merged_tree,
    load_latest_delta_tree,
    LoadStructuredDataError,
)
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.plugins.visuals.utils import VisualType
from cmk.gui.type_defs import HTTPVariables, PermittedViewSpecs, VisualContext
from cmk.gui.valuespec import Hostname
from cmk.gui.views.store import get_permitted_views


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

    def link_from(  # type:ignore[no-untyped-def]
        self, linking_view, linking_view_rows, visual, context_vars: HTTPVariables
    ) -> bool:
        """This has been implemented for HW/SW inventory views which are often useless when a host
        has no such information available. For example the "Oracle Tablespaces" inventory view is
        useless on hosts that don't host Oracle databases."""
        result = super().link_from(linking_view, linking_view_rows, visual, context_vars)
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

        # TODO: host is not correctly validated by visuals. Do it here for the moment.
        try:
            Hostname().validate_value(hostname, None)
        except MKUserError:
            return False

        if not (site_id := context.get("site")):
            return False

        return _has_inventory_tree(
            HostName(hostname),
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree", []),
            is_history=False,
        ) or _has_inventory_tree(
            HostName(hostname),
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree_history", []),
            is_history=True,
        )


def _has_inventory_tree(
    hostname: HostName,
    site_id: SiteId,
    paths: Sequence[SDPath],
    is_history: bool,
) -> bool:
    if not paths:
        return False

    # FIXME In order to decide whether this view is enabled
    # do we really need to load the whole tree?
    try:
        struct_tree = _get_struct_tree(is_history, hostname, site_id)
    except LoadStructuredDataError:
        return False

    if not struct_tree:
        return False

    if struct_tree.is_empty():
        return False

    return any(
        (node := struct_tree.get_node(path)) is not None and not node.is_empty() for path in paths
    )


def _get_struct_tree(
    is_history: bool, hostname: HostName, site_id: SiteId
) -> StructuredDataNode | None:
    struct_tree_cache = g.setdefault("struct_tree_cache", {})
    cache_id = (is_history, hostname, site_id)
    if cache_id in struct_tree_cache:
        return struct_tree_cache[cache_id]

    if is_history:
        struct_tree = load_latest_delta_tree(hostname)
    else:
        row = get_status_data_via_livestatus(site_id, hostname)
        struct_tree = load_filtered_and_merged_tree(row)

    struct_tree_cache[cache_id] = struct_tree
    return struct_tree
