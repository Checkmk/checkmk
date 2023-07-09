#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint

import cmk.utils.version as cmk_version
from cmk.utils.user import UserId

import cmk.gui.pages
import cmk.gui.pagetypes as pagetypes
from cmk.gui.config import active_config
from cmk.gui.dashboard import get_permitted_dashboards
from cmk.gui.hooks import request_memoize
from cmk.gui.http import response
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.node_visualization import ParentChildTopologyPage
from cmk.gui.plugins.sidebar import search
from cmk.gui.plugins.sidebar.utils import (
    footnotelinks,
    make_topic_menu,
    show_topic_menu,
    SidebarSnapin,
    snapin_registry,
)
from cmk.gui.type_defs import MegaMenu, TopicMenuTopic, Visual
from cmk.gui.views.store import get_permitted_views

if cmk_version.edition() is not cmk_version.Edition.CRE:
    import cmk.gui.cee.reporting as reporting  # pylint: disable=no-name-in-module
else:
    reporting = None  # type: ignore[assignment]


@snapin_registry.register
class Views(SidebarSnapin):
    @staticmethod
    def type_name():
        return "views"

    @classmethod
    def title(cls):
        return _("Views")

    @classmethod
    def description(cls):
        return _("Links to global views and dashboards")

    def show(self):
        show_topic_menu(treename="views", menu=get_view_menu_items(include_reports=False))

        links = []
        if user.may("general.edit_views"):
            if active_config.debug:
                links.append((_("Export"), "export_views.py"))
            links.append((_("Edit"), "edit_views.py"))
            footnotelinks(links)


@cmk.gui.pages.register("export_views")
def ajax_export_views() -> None:
    for view in get_permitted_views().values():
        view["owner"] = UserId.builtin()
        view["public"] = True
    response.set_data(pprint.pformat(get_permitted_views()))


@request_memoize()
def get_view_menu_items(include_reports: bool) -> list[TopicMenuTopic]:
    # The page types that are implementing the PageRenderer API should also be
    # part of the menu. Bring them into a visual like structure to make it easy to
    # integrate them.
    page_type_items: list[tuple[str, tuple[str, Visual]]] = []
    for page_type in pagetypes.all_page_types().values():
        if not issubclass(page_type, pagetypes.PageRenderer):
            continue

        for page in page_type.load().pages():
            if page._show_in_sidebar():
                visual = page.to_visual()
                visual["hidden"] = False  # Is currently to configurable for pagetypes
                visual["icon"] = None  # Is currently to configurable for pagetypes

                page_type_items.append((page_type.type_name(), (page.name(), visual)))

    # Apply some view specific filters
    views_to_show = [
        (name, view)
        for name, view in get_permitted_views().items()
        if (not active_config.visible_views or name in active_config.visible_views)
        and (not active_config.hidden_views or name not in active_config.hidden_views)
    ]

    network_topology_visual_spec = ParentChildTopologyPage.visual_spec()
    pages_to_show = [(network_topology_visual_spec["name"], network_topology_visual_spec)]

    visuals_to_show: list[tuple[str, tuple[str, Visual]]] = [
        ("views", (k, v)) for k, v in views_to_show
    ]
    visuals_to_show += [("dashboards", (k, v)) for k, v in get_permitted_dashboards().items()]
    visuals_to_show += [("pages", e) for e in pages_to_show]
    visuals_to_show += page_type_items

    if reporting and include_reports:
        reporting.load_reports()
        visuals_to_show += [("reports", (k, v)) for k, v in reporting.permitted_reports().items()]

    return make_topic_menu(visuals_to_show)


mega_menu_registry.register(
    MegaMenu(
        name="monitoring",
        title=_l("Monitor"),
        icon="main_monitoring",
        sort_index=5,
        topics=lambda: get_view_menu_items(include_reports=True),
        search=search.MonitoringSearch("monitoring_search"),
    )
)
