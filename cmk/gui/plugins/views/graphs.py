#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import time
from typing import Literal, Sequence

from cmk.gui.config import active_config
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics import html_render
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options
from cmk.gui.plugins.views.utils import (
    get_graph_timerange_from_painter_options,
    multisite_builtin_views,
    Painter,
    painter_option_registry,
    painter_registry,
    PainterOption,
    PainterOptions,
)
from cmk.gui.type_defs import ColumnName, TemplateGraphSpec
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import Dictionary, DropdownChoice, Transform, ValueSpec

multisite_builtin_views.update(
    {
        "service_graphs": {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "services",
            "description": _(
                "Shows all graphs including timerange selections " "of a collection of services."
            ),
            "group_painters": [
                ("sitealias", "sitehosts"),
                ("host_with_state", "host"),
                ("service_description", "service"),
            ],
            "hard_filters": [],
            "hard_filtervars": [],
            "hidden": True,
            "hide_filters": ["siteopt", "service", "host"],
            "layout": "boxed_graph",
            "mustsearch": False,
            "name": "service_graphs",
            "num_columns": 1,
            "owner": "",
            "painters": [
                ("service_graphs", None),
            ],
            "public": True,
            "show_filters": [],
            "sorters": [],
            "icon": "service_graph",
            "title": _("Service Graphs"),
            "topic": "history",
        },
        "host_graphs": {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "hosts",
            "description": _(
                "Shows host graphs including timerange selections " "of a collection of hosts."
            ),
            "group_painters": [
                ("sitealias", "sitehosts"),
                ("host_with_state", "host"),
            ],
            "hard_filters": [],
            "hard_filtervars": [],
            "hidden": True,
            "hide_filters": ["siteopt", "host"],
            "layout": "boxed_graph",
            "mustsearch": False,
            "name": "host_graphs",
            "num_columns": 1,
            "owner": "",
            "painters": [
                ("host_graphs", None),
            ],
            "public": True,
            "show_filters": [],
            "sorters": [],
            "icon": "graph",
            "title": _("Host graphs"),
            "topic": "history",
        },
    }
)


def paint_time_graph_cmk(row, cell, override_graph_render_options=None):
    graph_identification: tuple[Literal["template"], TemplateGraphSpec] = (
        "template",
        TemplateGraphSpec(
            {
                "site": row["site"],
                "host_name": row["host_name"],
                "service_description": row.get("service_description", "_HOST_"),
            }
        ),
    )

    # Load the graph render options from
    # a) the painter parameters configured in the view
    # b) the painter options set per user and view

    painter_params = cell.painter_parameters()
    painter_params = _transform_old_graph_render_options(painter_params)

    graph_render_options = painter_params["graph_render_options"]

    if override_graph_render_options is not None:
        graph_render_options.update(override_graph_render_options)

    painter_options = PainterOptions.get_instance()
    options = painter_options.get_without_default("graph_render_options")
    if options is not None:
        graph_render_options.update(options)

    now = int(time.time())
    if "set_default_time_range" in painter_params:
        duration = painter_params["set_default_time_range"]
        time_range = now - duration, now
    else:
        time_range = now - 3600 * 4, now

    # Load timerange from painter option (overrides the defaults, if set by the user)
    painter_option_pnp_timerange = painter_options.get_without_default("pnp_timerange")
    if painter_option_pnp_timerange is not None:
        time_range = get_graph_timerange_from_painter_options()

    graph_data_range = html_render.make_graph_data_range(time_range, graph_render_options)

    if is_mobile(request, response):
        graph_render_options.update(
            {
                "interaction": False,
                "show_controls": False,
                "show_pin": False,
                "show_graph_time": False,
                "show_time_range_previews": False,
                "show_legend": False,
                # Would be much better to autodetect the possible size (like on dashboard)
                "size": (27, 18),  # ex
            }
        )

    if "host_metrics" in row:
        available_metrics = row["host_metrics"]
        perf_data = row["host_perf_data"]
    else:
        available_metrics = row["service_metrics"]
        perf_data = row["service_perf_data"]

    if not available_metrics and perf_data:
        return "", _(
            "No historic metrics recorded but performance data is available. "
            "Maybe performance data processing is disabled."
        )

    return "", html_render.render_graphs_from_specification_html(
        graph_identification, graph_data_range, graph_render_options
    )


def paint_cmk_graphs_with_timeranges(row, cell):
    return paint_time_graph_cmk(
        row, cell, override_graph_render_options={"show_time_range_previews": True}
    )


def cmk_time_graph_params():
    elements = [
        (
            "set_default_time_range",
            DropdownChoice(
                title=_("Set default time range"),
                choices=[
                    (entry["duration"], entry["title"]) for entry in active_config.graph_timeranges
                ],
            ),
        ),
        ("graph_render_options", vs_graph_render_options()),
    ]

    return Transform(
        valuespec=Dictionary(
            elements=elements,
            optional_keys=[],
        ),
        forth=_transform_old_graph_render_options,
    )


def _transform_old_graph_render_options(value):
    if value is None:
        value = {}

    # Be compatible to pre 1.5.0i2 format
    if "graph_render_options" not in value:
        value = copy.deepcopy(value)
        value["graph_render_options"] = {
            "show_legend": value.pop("show_legend", True),
            "show_controls": value.pop("show_controls", True),
            "show_time_range_previews": value.pop("show_time_range_previews", True),
        }
    return value


@painter_registry.register
class PainterServiceGraphs(Painter):
    @property
    def ident(self) -> str:
        return "service_graphs"

    def title(self, cell):
        return _("Service Graphs with Timerange Previews")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return [
            "host_name",
            "service_description",
            "service_perf_data",
            "service_metrics",
            "service_check_command",
        ]

    @property
    def printable(self):
        return "time_graph"

    @property
    def painter_options(self):
        return ["pnp_timerange", "graph_render_options"]

    @property
    def parameters(self):
        return cmk_time_graph_params()

    def render(self, row, cell):
        return paint_cmk_graphs_with_timeranges(row, cell)


@painter_registry.register
class PainterHostGraphs(Painter):
    @property
    def ident(self) -> str:
        return "host_graphs"

    def title(self, cell):
        return _("Host Graphs with Timerange Previews")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_perf_data", "host_metrics", "host_check_command"]

    @property
    def printable(self):
        return "time_graph"

    @property
    def painter_options(self):
        return ["pnp_timerange", "graph_render_options"]

    @property
    def parameters(self):
        return cmk_time_graph_params()

    def render(self, row, cell):
        return paint_cmk_graphs_with_timeranges(row, cell)


@painter_option_registry.register
class PainterOptionGraphRenderOptions(PainterOption):
    @property
    def ident(self) -> str:
        return "graph_render_options"

    @property
    def valuespec(self) -> ValueSpec:
        return vs_graph_render_options()


def cmk_graph_url(row, what):
    site_id = row["site"]

    urivars = [
        ("siteopt", site_id),
        ("host", row["host_name"]),
    ]

    if what == "service":
        urivars += [
            ("service", row["service_description"]),
            ("view_name", "service_graphs"),
        ]
    else:
        urivars.append(("view_name", "host_graphs"))

    return makeuri_contextless(request, urivars, filename="view.py")
