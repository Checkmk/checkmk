#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple

import cmk.gui.dashboard as dashboard
import cmk.gui.pagetypes as pagetypes
import cmk.gui.views as views
from cmk.gui.config import active_config
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
        show_topic_menu(treename="views", menu=get_view_menu_items())

        links = []
        if user.may("general.edit_views"):
            if active_config.debug:
                links.append((_("Export"), "export_views.py"))
            links.append((_("Edit"), "edit_views.py"))
            footnotelinks(links)


def get_view_menu_items() -> List[TopicMenuTopic]:
    # The page types that are implementing the PageRenderer API should also be
    # part of the menu. Bring them into a visual like structure to make it easy to
    # integrate them.
    page_type_items: List[Tuple[str, Tuple[str, Visual]]] = []
    for page_type in pagetypes.all_page_types().values():
        if not issubclass(page_type, pagetypes.PageRenderer):
            continue

        for page in page_type.pages():
            if page._show_in_sidebar():
                visual = page.internal_representation().copy()
                visual["hidden"] = False  # Is currently to configurable for pagetypes
                visual["icon"] = None  # Is currently to configurable for pagetypes

                page_type_items.append((page_type.type_name(), (page.name(), visual)))

    # Apply some view specific filters
    views_to_show = [
        (name, view)
        for name, view in views.get_permitted_views().items()
        if (not active_config.visible_views or name in active_config.visible_views)
        and (not active_config.hidden_views or name not in active_config.hidden_views)
    ]

    network_topology_visual_spec = ParentChildTopologyPage.visual_spec()
    pages_to_show = [(network_topology_visual_spec["name"], network_topology_visual_spec)]

    visuals_to_show = [("views", e) for e in views_to_show]
    visuals_to_show += [("dashboards", e) for e in dashboard.get_permitted_dashboards().items()]
    visuals_to_show += [("pages", e) for e in pages_to_show]
    visuals_to_show += page_type_items

    return make_topic_menu(visuals_to_show)


mega_menu_registry.register(
    MegaMenu(
        name="monitoring",
        title=_l("Monitor"),
        icon="main_monitoring",
        sort_index=5,
        topics=get_view_menu_items,
        search=search.MonitoringSearch("monitoring_search"),
    )
)
