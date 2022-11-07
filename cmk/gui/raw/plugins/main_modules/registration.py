#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Sequence

import cmk.gui.pages
import cmk.gui.plugins.metrics.graph_images as graph_images
import cmk.gui.plugins.metrics.html_render as html_render
import cmk.gui.plugins.views.graphs as graphs
import cmk.gui.plugins.views.painters as painters
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.i18n import _
from cmk.gui.metrics import page_graph_dashlet, page_host_service_graph_popup
from cmk.gui.painters.v0.base import Cell, painter_registry
from cmk.gui.plugins.metrics.utils import CombinedGraphMetricSpec
from cmk.gui.plugins.visuals.utils import visual_type_registry
from cmk.gui.type_defs import CombinedGraphSpec, Row
from cmk.gui.view_utils import CellSpec
from cmk.gui.views import datasource_selection
from cmk.gui.views.host_tag_plugins import register_tag_plugins
from cmk.gui.views.page_ajax_filters import AjaxInitialViewFilters
from cmk.gui.views.page_ajax_popup_action_menu import ajax_popup_action_menu
from cmk.gui.views.page_ajax_reschedule import PageRescheduleCheck
from cmk.gui.views.page_create_view import page_create_view
from cmk.gui.views.page_edit_view import page_edit_view, PageAjaxCascadingRenderPainterParameters
from cmk.gui.views.page_edit_views import page_edit_views
from cmk.gui.views.page_show_view import page_show_view
from cmk.gui.views.visual_type import VisualTypeViews


def resolve_combined_single_metric_spec(
    specification: CombinedGraphSpec,
) -> Sequence[CombinedGraphMetricSpec]:
    # Not available in CRE.
    return ()


def painter_downtime_recurring_renderer(row: Row, cell: Cell) -> CellSpec:
    return "", _("(not supported)")


def register_pages() -> None:
    for path, callback in (
        ("host_service_graph_popup", page_host_service_graph_popup),
        ("graph_dashlet", page_graph_dashlet),
        ("noauth:ajax_graph_images", graph_images.ajax_graph_images_for_notifications),
        ("ajax_graph", html_render.ajax_graph),
        ("ajax_render_graph_content", html_render.ajax_render_graph_content),
        ("ajax_graph_hover", html_render.ajax_graph_hover),
    ):
        cmk.gui.pages.register(path)(partial(callback, resolve_combined_single_metric_spec))

    cmk.gui.pages.register("view")(page_show_view)
    cmk.gui.pages.register("create_view")(datasource_selection.page_create_view)
    cmk.gui.pages.register("edit_view")(page_edit_view)
    cmk.gui.pages.register("edit_views")(page_edit_views)
    cmk.gui.pages.register("create_view_infos")(page_create_view)
    cmk.gui.pages.register("ajax_popup_action_menu")(ajax_popup_action_menu)
    cmk.gui.pages.page_registry.register_page("ajax_cascading_render_painer_parameters")(
        PageAjaxCascadingRenderPainterParameters
    )
    cmk.gui.pages.page_registry.register_page("ajax_reschedule")(PageRescheduleCheck)
    cmk.gui.pages.page_registry.register_page("ajax_initial_view_filters")(AjaxInitialViewFilters)


def register_painters() -> None:
    graphs.PainterServiceGraphs.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    graphs.PainterHostGraphs.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    painters.PainterSvcPnpgraph.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    painters.PainterHostPnpgraph.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )

    painter_registry.register(graphs.PainterServiceGraphs)
    painter_registry.register(graphs.PainterHostGraphs)
    painter_registry.register(painters.PainterSvcPnpgraph)
    painter_registry.register(painters.PainterHostPnpgraph)

    painters.PainterDowntimeRecurring.renderer = painter_downtime_recurring_renderer
    painter_registry.register(painters.PainterDowntimeRecurring)


register_pages()
register_painters()
register_post_config_load_hook(register_tag_plugins)
visual_type_registry.register(VisualTypeViews)
