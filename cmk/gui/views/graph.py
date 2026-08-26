#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import copy
import time
from collections.abc import Sequence
from dataclasses import replace
from typing import Literal, override

from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.graphing import (
    get_template_graph_specification,
    GraphDisplayConfigHTML,
    GraphRenderOptions,
    render_engine_graph_group,
    resolve_size,
    TemplateGraphSpecification,
    vs_graph_render_options,
)
from cmk.gui.graphing._frontend import (
    _DEFAULT_INTERACTION,
    default_time_range_seconds,
    STATIC_INTERACTION,
)
from cmk.gui.http import Request, Response, response
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter_options import (
    PainterOption,
    PainterOptionRegistry,
    PainterOptions,
)
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    DynamicIconName,
    PainterParameters,
    Row,
    ViewName,
    ViewSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    MigrateNotUpdated,
    Timerange,
    Transform,
)
from cmk.gui.view_utils import (
    CellSpec,
    CSVExportError,
    JSONExportError,
    PythonExportError,
)
from cmk.shared_typing.cmk_time_series_graph import Size
from cmk.web.utils.html import HTML
from cmk.web.utils.urls import makeuri_contextless

# Options only the legacy renderer honoured; the graph engine ignores them.
_LEGACY_ONLY_RENDER_OPTIONS = (
    "font_size",
    "title_format",
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
    user: LoggedInUser,
    request: Request,
    response: Response,
    painter_options: PainterOptions,
    show_time_range_previews: bool | None = None,
    require_historic_metrics: bool = True,
) -> tuple[Literal[""], HTML | str]:
    # Load the graph render options from
    # a) the painter parameters configured in the view
    # b) the painter options set per user and view

    painter_params = cell.painter_parameters()
    painter_params = _migrate_old_graph_render_options(painter_params)

    graph_render_options = painter_params["graph_render_options"].copy()
    if show_time_range_previews is not None:
        graph_render_options["show_time_range_previews"] = show_time_range_previews

    options = painter_options.get_without_default("graph_render_options")
    if options is not None:
        graph_render_options.update(options)

    view_options = GraphRenderOptions.from_graph_render_options_vs(graph_render_options)
    graph_size = resolve_size(view_options)

    display_config = GraphDisplayConfigHTML.from_options(
        theme.get(),
        view_options,
    )

    now = int(time.time())
    if "set_default_time_range" in painter_params:
        duration = painter_params["set_default_time_range"]
        raw_time_range: tuple[int, int] = (now - duration, now)
    else:
        raw_time_range = (now - default_time_range_seconds(), now)

    # The engine takes its interactions as an explicit argument rather than off the display
    # config, so a mobile render has to hand it the static one.
    mobile = is_mobile(request, response)
    if mobile:
        graph_size = (27.0, 18.0)
        display_config = display_config.model_copy(
            update={
                "show_pin": False,
                "show_time_range_previews": False,
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

    graph_specification = get_template_graph_specification(
        site_id=row["site"],
        host_name=row["host_name"],
        service_name=row.get("service_description", "_HOST_"),
    )

    return "", _render_engine_graph_group(
        row,
        graph_specification,
        display_config,
        graph_size=graph_size,
        raw_time_range=raw_time_range,
        debug=debug,
        mobile=mobile,
    )


def _render_engine_graph_group(
    row: Row,
    graph_specification: TemplateGraphSpecification,
    display_config: GraphDisplayConfigHTML,
    *,
    graph_size: tuple[float, float],
    raw_time_range: tuple[int, int],
    debug: bool,
    mobile: bool,
) -> HTML:
    """Render the graph-engine (Vue) graph group for a row's template graphs."""
    return render_engine_graph_group(
        graph_specification,
        host_name=row["host_name"],
        service_name=row.get("service_description", "_HOST_"),
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
                _DEFAULT_INTERACTION, pin="enabled" if display_config.show_pin else "disabled"
            )
        ),
        show_graph_time=display_config.show_time_range_previews,
        show_legend=display_config.show_legend,
        debug=debug,
        full_width=True,
    )


def _vs_graph_render_options_for_views() -> MigrateNotUpdated:
    return vs_graph_render_options(exclude=_LEGACY_ONLY_RENDER_OPTIONS, with_inline_title=False)


def cmk_time_graph_params() -> MigrateNotUpdated:
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


class PainterServiceGraphs(Painter):
    @property
    @override
    def ident(self) -> str:
        return "service_graphs"

    @override
    def title(self, cell: Cell) -> str:
        return _("Service graphs with time range previews")

    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return [
            "host_name",
            "service_description",
            "service_perf_data",
            "service_metrics",
            "service_check_command",
        ]

    @property
    @override
    def printable(self) -> str:
        return "time_graph"

    @property
    @override
    def painter_options(self) -> list[str]:
        # No pnp_timerange: the engine takes its time range from the global time picker.
        return ["graph_render_options"]

    @property
    @override
    def parameters(self) -> MigrateNotUpdated:
        return cmk_time_graph_params()

    @override
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            debug=self.config.debug,
            show_time_range_previews=True,
        )

    @override
    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError

    @override
    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError

    @override
    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError


class PainterHostGraphs(Painter):
    @property
    @override
    def ident(self) -> str:
        return "host_graphs"

    @override
    def title(self, cell: Cell) -> str:
        return _("Host graphs with time range previews")

    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_perf_data", "host_metrics", "host_check_command"]

    @property
    @override
    def printable(self) -> str:
        return "time_graph"

    @property
    @override
    def painter_options(self) -> list[str]:
        # No pnp_timerange: the engine takes its time range from the global time picker.
        return ["graph_render_options"]

    @property
    @override
    def parameters(self) -> MigrateNotUpdated:
        return cmk_time_graph_params()

    @override
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            debug=self.config.debug,
            show_time_range_previews=True,
            # for PainterHostGraphs used to paint service graphs (view "Service graphs of host"),
            # also render the graphs if there are no historic metrics available (but perf data is)
            require_historic_metrics="service_description" not in row,
        )

    @override
    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError

    @override
    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError

    @override
    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError


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


class PainterSvcPnpgraph(Painter):
    @property
    @override
    def ident(self) -> str:
        return "svc_pnpgraph"

    @override
    def title(self, cell: Cell) -> str:
        return _("Service graphs")

    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return [
            "host_name",
            "service_description",
            "service_perf_data",
            "service_metrics",
            "service_check_command",
        ]

    @property
    @override
    def printable(self) -> str:
        return "time_graph"

    @property
    @override
    def painter_options(self) -> list[str]:
        # No pnp_timerange: the engine takes its time range from the global time picker.
        return []

    @property
    @override
    def parameters(self) -> Transform:
        return cmk_time_graph_params()

    @override
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            debug=self.config.debug,
        )

    @override
    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError

    @override
    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError

    @override
    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError


class PainterHostPnpgraph(Painter):
    @property
    @override
    def ident(self) -> str:
        return "host_pnpgraph"

    @override
    def title(self, cell: Cell) -> str:
        return _("Host graph")

    @override
    def short_title(self, cell: Cell) -> str:
        return _("Graph")

    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_perf_data", "host_metrics", "host_check_command"]

    @property
    @override
    def printable(self) -> str:
        return "time_graph"

    @property
    @override
    def painter_options(self) -> list[str]:
        # No pnp_timerange: the engine takes its time range from the global time picker.
        return []

    @property
    @override
    def parameters(self) -> Transform:
        return cmk_time_graph_params()

    @override
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            debug=self.config.debug,
        )

    @override
    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError

    @override
    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError

    @override
    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError


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
