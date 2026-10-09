#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import copy
import time
from dataclasses import replace
from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui.graphing import (
    DEFAULT_INTERACTION,
    default_time_range_seconds,
    EngineDisplayOptions,
    get_temperature_unit,
    GraphDisplayConfigHTML,
    GraphRenderOptions,
    render_engine_graph_group,
    resolve_size,
    STATIC_INTERACTION,
    stored_time_range_seconds,
    TemplateGraphSpecification,
    vs_graph_render_options,
)
from cmk.gui.http import Request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter import Cell, InternalPainter, PainterContext
from cmk.gui.painter_options import (
    PainterOption,
    PainterOptionRegistry,
    PainterOptions,
)
from cmk.gui.type_defs import (
    ColumnSpec,
    PainterParameters,
    Row,
    ViewName,
    ViewSpec,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    MigrateNotUpdated,
    Timerange,
)
from cmk.gui.view_utils import (
    CellSpec,
    CSVExportError,
    JSONExportError,
    PythonExportError,
)
from cmk.shared_typing.cmk_time_series_graph import Size
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import DynamicIconName
from cmk.web.utils.urls import makeuri_contextless

# Options only the legacy renderer honoured; the graph engine ignores them.
_LEGACY_ONLY_RENDER_OPTIONS = (
    "font_size",
    "title_format",
    "show_margin",
    "show_time_range_previews",
    "fixed_timerange",
)


def register(
    painter_option_registry: PainterOptionRegistry,
    multisite_builtin_views: dict[ViewName, ViewSpec],
) -> None:
    painter_option_registry.register(PainterOptionGraphRenderOptions())
    # No graph painter declares "pnp_timerange" any more - the engine takes its time range
    # from the global time picker. The option stays registered because the reporting instant
    # view still reads its valuespec (nonfree/pro/reporting/_page_instant_view.py).
    painter_option_registry.register(PainterOptionPNPTimerange())

    multisite_builtin_views.update(_GRAPH_VIEWS)


_GRAPH_VIEWS = {
    "service_graphs": ViewSpec(
        {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "services",
            "description": _l(
                "Shows all graphs including time range selections of a collection of services."
            ),
            "group_painters": [],
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
            "icon": DynamicIconName("service_graph"),
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
            "main_menu_search_terms": [],
        }
    ),
    "host_graphs": ViewSpec(
        {
            "browser_reload": 30,
            "column_headers": "off",
            "datasource": "hosts",
            "description": _l(
                "Shows host graphs including time range selections of a collection of hosts."
            ),
            "group_painters": [],
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
            "icon": DynamicIconName("host_graph"),
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
            "main_menu_search_terms": [],
        }
    ),
}


def _paint_time_graph_cmk(
    row: Row,
    cell: Cell,
    *,
    debug: bool,
    mobile: bool,
    painter_options: PainterOptions,
    temperature_unit: TemperatureUnit,
    require_historic_metrics: bool = True,
) -> tuple[Literal[""], HTML | str]:
    # Load the graph render options from
    # a) the painter parameters configured in the view
    # b) the painter options set per user and view

    painter_params = cell.painter_parameters()
    painter_params = _migrate_old_graph_render_options(painter_params)

    graph_render_options = painter_params["graph_render_options"].copy()

    options = painter_options.get_without_default("graph_render_options")
    if options is not None:
        graph_render_options.update(options)

    view_options = GraphRenderOptions.from_graph_render_options_vs(graph_render_options)
    graph_size = resolve_size(view_options)

    display_config = GraphDisplayConfigHTML.from_options(
        view_options,
    )

    now = int(time.time())
    duration = stored_time_range_seconds(
        painter_parameters=painter_params, stored_by_the_view=cell.has_painter_params()
    )
    if duration is None:
        duration = default_time_range_seconds()
    raw_time_range: tuple[int, int] = (now - duration, now)

    # The engine takes its interactions as an explicit argument rather than off the display
    # config, so a mobile render has to hand it the static one.
    if mobile:
        graph_size = (27.0, 18.0)
        display_config = display_config.model_copy(
            update={
                "show_pin": False,
                "show_graph_time": False,
                "show_legend": False,
            }
        )

    if "host_metrics" in row:
        available_metrics = row["host_metrics"]
        perf_data = row["host_perf_data"]
    else:
        available_metrics = row["service_metrics"]
        perf_data = row["service_perf_data"]

    if not available_metrics and perf_data and require_historic_metrics:
        return "", _(
            "No historic metrics recorded but metrics are available. "
            "Maybe metrics processing is disabled."
        )

    graph_specification = TemplateGraphSpecification(
        site=row["site"],
        host_name=row["host_name"],
        service_description=row.get("service_description", "_HOST_"),
    )

    return "", _render_engine_graph_group(
        graph_specification,
        display_config,
        graph_size=graph_size,
        raw_time_range=raw_time_range,
        debug=debug,
        mobile=mobile,
        temperature_unit=temperature_unit,
    )


def _render_engine_graph_group(
    graph_specification: TemplateGraphSpecification,
    display_config: GraphDisplayConfigHTML,
    *,
    graph_size: tuple[float, float],
    raw_time_range: tuple[int, int],
    debug: bool,
    mobile: bool,
    temperature_unit: TemperatureUnit,
) -> HTML:
    """Render the graph-engine (Vue) graph group for a row's template graphs."""
    return render_engine_graph_group(
        graph_specification,
        size=Size(
            width=graph_size[0],
            height=graph_size[1],
            mode="resizable" if display_config.resizable else "fixed",
        ),
        time_range=raw_time_range,
        interaction=(
            STATIC_INTERACTION
            if mobile
            else replace(
                DEFAULT_INTERACTION,
                burger="enabled" if display_config.show_controls else "disabled",
                pin="enabled" if display_config.show_pin else "disabled",
            )
        ),
        show_graph_time=display_config.show_graph_time,
        display=EngineDisplayOptions(
            show_legend=display_config.show_legend,
            show_title=bool(display_config.show_title),
            show_vertical_axis=display_config.show_vertical_axis,
            show_time_axis=display_config.show_time_axis,
            vertical_axis_width=display_config.vertical_axis_width,
        ),
        debug=debug,
        full_width=True,
        temperature_unit=temperature_unit,
    )


def _vs_graph_render_options_for_views() -> MigrateNotUpdated:
    return vs_graph_render_options(exclude=_LEGACY_ONLY_RENDER_OPTIONS, with_inline_title=False)


def cmk_time_graph_params(context: PainterContext) -> MigrateNotUpdated:
    elements = [
        (
            "set_default_time_range",
            DropdownChoice(
                title=_("Set default time range"),
                choices=[
                    (entry["duration"], entry["title"]) for entry in context.config.graph_timeranges
                ],
            ),
        ),
        ("graph_render_options", _vs_graph_render_options_for_views()),
    ]

    return MigrateNotUpdated(
        valuespec=Dictionary(
            elements=elements,
            optional_keys=[],
        ),
        migrate=_migrate_old_graph_render_options,
    )


def _migrate_old_graph_render_options(value: PainterParameters | None) -> PainterParameters:
    if value is None:
        value = {}

    # Be compatible to pre 1.5.0i2 format
    if "graph_render_options" not in value:
        value = copy.deepcopy(value)
        value["graph_render_options"] = {
            "show_legend": value.pop("show_legend", True),  # type: ignore[typeddict-item]
            "show_controls": value.pop("show_controls", True),  # type: ignore[typeddict-item]
            "show_time_range_previews": value.pop("show_time_range_previews", True),  # type: ignore[typeddict-item]
        }
    return value


def _render_service_graphs(
    row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_time_graph_cmk(
        row,
        cell,
        mobile=context.url_renderer.is_mobile(),
        painter_options=context.painter_options,
        debug=context.config.debug,
        temperature_unit=get_temperature_unit(acting_user, context.config.default_temperature_unit),
    )


def _export_for_python_service_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise PythonExportError


def _export_for_csv_service_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_service_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise JSONExportError


def make_service_graphs_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_graphs",
        title=_l("Service graphs with display options"),
        columns=[
            "host_name",
            "service_description",
            "service_perf_data",
            "service_metrics",
            "service_check_command",
        ],
        printable="time_graph",
        painter_options=["graph_render_options"],
        parameters=cmk_time_graph_params,
        render=_render_service_graphs,
        export_for_python=_export_for_python_service_graphs,
        export_for_csv=_export_for_csv_service_graphs,
        export_for_json=_export_for_json_service_graphs,
    )


def _render_host_graphs(
    row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_time_graph_cmk(
        row,
        cell,
        mobile=context.url_renderer.is_mobile(),
        painter_options=context.painter_options,
        debug=context.config.debug,
        temperature_unit=get_temperature_unit(acting_user, context.config.default_temperature_unit),
        # for PainterHostGraphs used to paint service graphs (view "Service graphs of host"),
        # also render the graphs if there are no historic metrics available (but perf data is)
        require_historic_metrics="service_description" not in row,
    )


def _export_for_python_host_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise PythonExportError


def _export_for_csv_host_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_host_graphs(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise JSONExportError


def make_host_graphs_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_graphs",
        title=_l("Host graphs with display options"),
        columns=["host_name", "host_perf_data", "host_metrics", "host_check_command"],
        printable="time_graph",
        painter_options=["graph_render_options"],
        parameters=cmk_time_graph_params,
        render=_render_host_graphs,
        export_for_python=_export_for_python_host_graphs,
        export_for_csv=_export_for_csv_host_graphs,
        export_for_json=_export_for_json_host_graphs,
    )


class PainterOptionGraphRenderOptions(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="graph_render_options", valuespec=_vs_graph_render_options_for_views()
        )


class PainterOptionPNPTimerange(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="pnp_timerange",
            valuespec=Timerange(
                title=_("Graph time range"),
                default_value=None,
                include_time=True,
            ),
        )


def _render_svc_pnpgraph(
    row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_time_graph_cmk(
        row,
        cell,
        mobile=context.url_renderer.is_mobile(),
        painter_options=context.painter_options,
        debug=context.config.debug,
        temperature_unit=get_temperature_unit(acting_user, context.config.default_temperature_unit),
    )


def _export_for_python_svc_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise PythonExportError


def _export_for_csv_svc_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_svc_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise JSONExportError


def make_svc_pnpgraph_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_pnpgraph",
        title=_l("Service graphs"),
        columns=[
            "host_name",
            "service_description",
            "service_perf_data",
            "service_metrics",
            "service_check_command",
        ],
        printable="time_graph",
        painter_options=[],
        parameters=cmk_time_graph_params,
        render=_render_svc_pnpgraph,
        export_for_python=_export_for_python_svc_pnpgraph,
        export_for_csv=_export_for_csv_svc_pnpgraph,
        export_for_json=_export_for_json_svc_pnpgraph,
    )


def _render_host_pnpgraph(
    row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_time_graph_cmk(
        row,
        cell,
        mobile=context.url_renderer.is_mobile(),
        painter_options=context.painter_options,
        debug=context.config.debug,
        temperature_unit=get_temperature_unit(acting_user, context.config.default_temperature_unit),
    )


def _export_for_python_host_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise PythonExportError


def _export_for_csv_host_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_host_pnpgraph(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    raise JSONExportError


def make_host_pnpgraph_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_pnpgraph",
        title=_l("Host graph"),
        short_title=_l("Graph"),
        columns=["host_name", "host_perf_data", "host_metrics", "host_check_command"],
        printable="time_graph",
        painter_options=[],
        parameters=cmk_time_graph_params,
        render=_render_host_pnpgraph,
        export_for_python=_export_for_python_host_pnpgraph,
        export_for_csv=_export_for_csv_host_pnpgraph,
        export_for_json=_export_for_json_host_pnpgraph,
    )


def cmk_graph_url(row: Row, what: str, *, request: Request) -> str:
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
