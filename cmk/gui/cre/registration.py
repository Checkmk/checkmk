#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raw edition and only raw edition specific registrations"""

import cmk.gui.graphing._graph_images as graph_images
import cmk.gui.graphing._html_render as html_render
import cmk.gui.pages
from cmk.gui import sidebar, visuals
from cmk.gui.dashboard import dashlet_registry
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.metrics import PageGraphDashlet, PageHostServiceGraphPopup
from cmk.gui.pages import page_registry
from cmk.gui.painter.v0.base import painter_registry
from cmk.gui.permissions import permission_section_registry
from cmk.gui.sidebar import snapin_registry
from cmk.gui.sites import site_choices
from cmk.gui.valuespec import autocompleter_registry
from cmk.gui.views import graph
from cmk.gui.visuals import default_site_filter_heading_info
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.wato import notification_parameter_registry, NotificationParameterMail


def register_pages() -> None:
    cmk.gui.pages.page_registry.register(PageGraphDashlet)
    cmk.gui.pages.page_registry.register(PageHostServiceGraphPopup)
    cmk.gui.pages.page_registry.register(html_render.AjaxRenderGraphContent)
    cmk.gui.pages.page_registry.register(html_render.AjaxGraphHover)
    cmk.gui.pages.page_registry.register(html_render.AjaxGraph)
    cmk.gui.pages.page_registry.register(graph_images.AjaxGraphImagesForNotifications)


def register_painters() -> None:
    painter_registry.register(graph.PainterServiceGraphs)
    painter_registry.register(graph.PainterHostGraphs)
    painter_registry.register(graph.PainterSvcPnpgraph)
    painter_registry.register(graph.PainterHostPnpgraph)


def register() -> None:
    visuals.register(
        page_registry,
        visual_info_registry,
        filter_registry,
        autocompleter_registry,
        site_choices,
        default_site_filter_heading_info,
    )
    sidebar.register(
        page_registry,
        permission_section_registry,
        snapin_registry,
        dashlet_registry,
        mega_menu_registry,
        view_menu_topics=sidebar.default_view_menu_topics,
    )
    notification_parameter_registry.register(NotificationParameterMail)
    register_pages()
    register_painters()
