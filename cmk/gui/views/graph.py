#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import time
from collections.abc import Callable, Sequence
from typing import Literal

from cmk.utils.type_defs import UserId

from cmk.gui.config import active_config
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _l
from cmk.gui.plugins.metrics import html_render
from cmk.gui.plugins.metrics.utils import CombinedGraphMetricSpec
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    CombinedGraphSpec,
    Row,
    TemplateGraphSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    MigrateNotUpdated,
    Timerange,
    Transform,
    ValueSpec,
)
from cmk.gui.view_utils import CellSpec, CSVExportError, JSONExportError, PythonExportError

from .painter.v0.base import Cell, Painter2
from .painter_options import (
    get_graph_timerange_from_painter_options,
    painter_option_registry,
    PainterOption,
    PainterOptions,
)
from .store import multisite_builtin_views

multisite_builtin_views.update(
    {
        "service_graphs": {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "services",
            "description": _l(
                "Shows all graphs including timerange selections of a collection of services."
            ),
            "group_painters": [
                ColumnSpec(
                    name="sitealias",
                    link_spec=VisualLinkSpec(type_name="views", name="sitehosts"),
                ),
                ColumnSpec(
                    name="host_with_state",
                    link_spec=VisualLinkSpec(type_name="views", name="host"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="service"),
                ),
            ],
            "hidden": True,
            "hidebutton": False,
            "layout": "boxed_graph",
            "mustsearch": False,
            "name": "service_graphs",
            "num_columns": 1,
            "owner": UserId.builtin(),
            "painters": [
                ColumnSpec(name="service_graphs"),
            ],
            "public": True,
            "sorters": [],
            "icon": "service_graph",
            "title": _l("Service graphs"),
            "topic": "history",
            "user_sortable": True,
            "single_infos": ["service", "host"],
            "context": {"siteopt": {}},
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
        },
        "host_graphs": {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "hosts",
            "description": _l(
                "Shows host graphs including timerange selections of a collection of hosts."
            ),
            "group_painters": [
                ColumnSpec(
                    name="sitealias",
                    link_spec=VisualLinkSpec(type_name="views", name="sitehosts"),
                ),
                ColumnSpec(
                    name="host_with_state",
                    link_spec=VisualLinkSpec(type_name="views", name="host"),
                ),
            ],
            "hidden": True,
            "hidebutton": False,
            "layout": "boxed_graph",
            "mustsearch": False,
            "name": "host_graphs",
            "num_columns": 1,
            "owner": UserId.builtin(),
            "painters": [ColumnSpec(name="host_graphs")],
            "public": True,
            "sorters": [],
            "icon": "host_graph",
            "title": _l("Host graphs"),
            "topic": "history",
            "user_sortable": True,
            "single_infos": ["host"],
            "context": {"siteopt": {}},
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
        },
    }
)


def paint_time_graph_cmk(  # type:ignore[no-untyped-def]
    row,
    cell,
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ],
    *,
    override_graph_render_options=None,
):
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
    painter_params = _migrate_old_graph_render_options(painter_params)

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
        graph_identification,
        graph_data_range,
        graph_render_options,
        resolve_combined_single_metric_spec,
    )


def paint_cmk_graphs_with_timeranges(  # type:ignore[no-untyped-def]
    row,
    cell,
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ],
):
    return paint_time_graph_cmk(
        row,
        cell,
        resolve_combined_single_metric_spec,
        override_graph_render_options={"show_time_range_previews": True},
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

    return MigrateNotUpdated(
        valuespec=Dictionary(
            elements=elements,
            optional_keys=[],
        ),
        migrate=_migrate_old_graph_render_options,
    )


def _migrate_old_graph_render_options(value):
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


class PainterServiceGraphs(Painter2):
    @property
    def ident(self) -> str:
        return "service_graphs"

    def title(self, cell):
        return _("Service graphs with timerange previews")

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

    def render(self, row: Row, cell: Cell) -> CellSpec:
        resolve_combined_single_metric_spec = type(self).resolve_combined_single_metric_spec
        assert resolve_combined_single_metric_spec is not None
        return paint_cmk_graphs_with_timeranges(
            row,
            cell,
            resolve_combined_single_metric_spec,
        )

    def export_for_python(self, row: Row, cell: Cell) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> object:
        raise JSONExportError()


class PainterHostGraphs(Painter2):
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

    def render(self, row: Row, cell: Cell) -> CellSpec:
        resolve_combined_single_metric_spec = type(self).resolve_combined_single_metric_spec
        assert resolve_combined_single_metric_spec is not None
        return paint_cmk_graphs_with_timeranges(
            row,
            cell,
            resolve_combined_single_metric_spec,
        )

    def export_for_python(self, row: Row, cell: Cell) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> object:
        raise JSONExportError()


@painter_option_registry.register
class PainterOptionGraphRenderOptions(PainterOption):
    @property
    def ident(self) -> str:
        return "graph_render_options"

    @property
    def valuespec(self) -> ValueSpec:
        return vs_graph_render_options()


@painter_option_registry.register
class PainterOptionPNPTimerange(PainterOption):
    @property
    def ident(self) -> str:
        return "pnp_timerange"

    @property
    def valuespec(self) -> Timerange:
        return Timerange(
            title=_("Graph time range"),
            default_value=None,
            include_time=True,
        )


class PainterSvcPnpgraph(Painter2):
    @property
    def ident(self) -> str:
        return "svc_pnpgraph"

    def title(self, cell: Cell) -> str:
        return _("Service graphs")

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
    def printable(self) -> str:
        return "time_graph"

    @property
    def painter_options(self) -> list[str]:
        return ["pnp_timerange", "show_internal_graph_and_metric_ids"]

    @property
    def parameters(self) -> Transform:
        return cmk_time_graph_params()

    def render(self, row: Row, cell: Cell) -> CellSpec:
        resolve_combined_single_metric_spec = type(self).resolve_combined_single_metric_spec
        assert resolve_combined_single_metric_spec is not None
        return paint_time_graph_cmk(row, cell, resolve_combined_single_metric_spec)

    def export_for_python(self, row: Row, cell: Cell) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> object:
        raise JSONExportError()


class PainterHostPnpgraph(Painter2):
    @property
    def ident(self) -> str:
        return "host_pnpgraph"

    def title(self, cell: Cell) -> str:
        return _("Host graph")

    def short_title(self, cell: Cell) -> str:
        return _("Graph")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_perf_data", "host_metrics", "host_check_command"]

    @property
    def printable(self) -> str:
        return "time_graph"

    @property
    def painter_options(self) -> list[str]:
        return ["pnp_timerange"]

    @property
    def parameters(self) -> Transform:
        return cmk_time_graph_params()

    def render(self, row: Row, cell: Cell) -> CellSpec:
        resolve_combined_single_metric_spec = type(self).resolve_combined_single_metric_spec
        assert resolve_combined_single_metric_spec is not None
        return paint_time_graph_cmk(row, cell, resolve_combined_single_metric_spec)

    def export_for_python(self, row: Row, cell: Cell) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> object:
        raise JSONExportError()


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
