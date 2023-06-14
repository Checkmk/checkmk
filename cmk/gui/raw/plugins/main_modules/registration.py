#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raw edition and only raw edition specific registrations"""

from collections.abc import Sequence
from functools import partial

import cmk.utils.version as cmk_version

import cmk.gui.pages
import cmk.gui.plugins.metrics.graph_images as graph_images
import cmk.gui.plugins.metrics.html_render as html_render
from cmk.gui.i18n import _
from cmk.gui.metrics import page_graph_dashlet, page_host_service_graph_popup
from cmk.gui.painter.v0 import painters
from cmk.gui.painter.v0.base import Cell, painter_registry
from cmk.gui.plugins.metrics.utils import CombinedGraphMetricSpec
from cmk.gui.type_defs import CombinedGraphSpec, Row
from cmk.gui.view_utils import CellSpec
from cmk.gui.views import graph


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


def register_painters() -> None:
    graph.PainterServiceGraphs.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    graph.PainterHostGraphs.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    graph.PainterSvcPnpgraph.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )
    graph.PainterHostPnpgraph.resolve_combined_single_metric_spec = (
        resolve_combined_single_metric_spec
    )

    painter_registry.register(graph.PainterServiceGraphs)
    painter_registry.register(graph.PainterHostGraphs)
    painter_registry.register(graph.PainterSvcPnpgraph)
    painter_registry.register(graph.PainterHostPnpgraph)

    painters.PainterDowntimeRecurring.renderer = painter_downtime_recurring_renderer
    painter_registry.register(painters.PainterDowntimeRecurring)


def register() -> None:
    if not cmk_version.is_raw_edition():
        return

    register_pages()
    register_painters()


register()
