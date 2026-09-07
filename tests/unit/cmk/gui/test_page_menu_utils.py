#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

import pytest

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import SDPath

from cmk.gui.dashboard import visual_type as dashboard_visual_type
from cmk.gui.http import request
from cmk.gui.page_menu import PageMenuLink
from cmk.gui.page_menu_utils import get_context_page_menu_dropdowns
from cmk.gui.type_defs import Rows, ViewName, VisualContext
from cmk.gui.view import View
from cmk.gui.views import visual_type as views_visual_type
from cmk.gui.views.store import multisite_builtin_views


def _page_menu_urls(view_name: ViewName, context: VisualContext, rows: Rows) -> dict[str, str]:
    view = View(view_name, multisite_builtin_views[view_name], context)
    return {
        entry.name: entry.item.link.url
        for dropdown in get_context_page_menu_dropdowns(view, rows, False)
        for topic in dropdown.topics
        for entry in topic.entries
        if entry.name is not None
        and isinstance(entry.item, PageMenuLink)
        and entry.item.link.url is not None
    }


def _restrict_linkable_visuals(
    monkeypatch: pytest.MonkeyPatch, view_names: Iterable[ViewName]
) -> None:
    """Link only to the given views to keep the test independent of the available visuals"""
    views = {name: multisite_builtin_views[name] for name in view_names}
    monkeypatch.setattr(views_visual_type, "get_permitted_views", lambda: views)
    monkeypatch.setattr(dashboard_visual_type, "get_permitted_dashboards", lambda: {})


def test_page_menu_link_to_servicedesc_is_not_restricted_to_the_current_site(
    ui_context: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _restrict_linkable_visuals(monkeypatch, ["servicedesc", "svcevents"])
    request.set_var("site", "central")

    urls = _page_menu_urls(
        "service",
        {"host": {"host": "myhost"}, "service": {"service": "Check_MK"}},
        [{"site": "central", "host_name": "myhost"}],
    )

    # The view shows the service of all hosts, so it must not be limited to a single site
    assert "site=" not in urls["cb_servicedesc"]
    # Single object views are still linked with the site to speed up their livestatus queries
    assert "site=central" in urls["cb_svcevents"]


def test_page_menu_link_to_inventory_view_knows_the_site(
    ui_context: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _restrict_linkable_visuals(monkeypatch, ["inv_host"])
    queried_sites: list[SiteId] = []

    def fake_has_inventory_tree(
        hostname: HostName,
        site_id: SiteId,
        path: SDPath | None,
        is_history: bool,
        tree_cache: object,
    ) -> bool:
        queried_sites.append(site_id)
        return True

    # Exception: patching a private function, as it is the only seam to observe which site
    # the inventory data is looked up for without providing real inventory trees on disk
    monkeypatch.setattr(views_visual_type, "_has_inventory_tree", fake_has_inventory_tree)
    request.set_var("site", "central")

    urls = _page_menu_urls("host", {"host": {"host": "myhost"}}, [{"site": "central"}])

    # link_from() needs the site to look up the inventory data of the host
    assert queried_sites == [SiteId("central")]
    assert "site=central" in urls["cb_inv_host"]
