#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raw edition and only raw edition specific registrations"""

import cmk.gui.graphing._graph_images as graph_images
import cmk.gui.graphing._html_render as html_render
import cmk.gui.pages
from cmk.gui.metrics import PageGraphDashlet, PageHostServiceGraphPopup
from cmk.gui.painter.v0.base import painter_registry
from cmk.gui.views import graph
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
    notification_parameter_registry.register(NotificationParameterMail)
    register_pages()
    register_painters()
