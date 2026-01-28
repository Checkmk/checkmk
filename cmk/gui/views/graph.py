#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import copy
import time
from collections.abc import Mapping, Sequence
from typing import Literal
from uuid import uuid4

from cmk.ccc.user import UserId
from cmk.ccc.version import edition
from cmk.graphing.v1 import graphs as graphs_api
from cmk.gui.config import active_config
from cmk.gui.graphing import (
    FetchTimeSeries,
    get_temperature_unit,
    get_template_graph_specification,
    GraphRenderConfig,
    GraphRenderOptions,
    graphs_from_api,
    make_graph_data_range,
    metric_backend_registry,
    metrics_from_api,
    RegisteredMetric,
    render_graphs_from_specification_html,
    vs_graph_render_options,
)
from cmk.gui.http import Request, Response, response
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter_options import (
    get_graph_timerange_from_painter_options,
    PainterOption,
    PainterOptionRegistry,
    PainterOptions,
)
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    DynamicIconName,
    GraphTimerange,
    PainterParameters,
    Row,
    ViewName,
    ViewSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.utils.urls import makeuri_contextless
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
from cmk.utils import paths


def register(
    painter_option_registry: PainterOptionRegistry,
    multisite_builtin_views: dict[ViewName, ViewSpec],
) -> None:
    painter_option_registry.register(PainterOptionGraphRenderOptions())
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
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    user_permissions: UserPermissions,
    *,
    debug: bool,
    graph_timeranges: Sequence[GraphTimerange],
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
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

    graph_render_config = GraphRenderConfig.from_user_context_and_options(
        user,
        theme.get(),
        GraphRenderOptions.from_graph_render_options_vs(graph_render_options),
    )

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

    graph_data_range = make_graph_data_range(
        time_range,
        graph_render_config.size[1],
    )

    if is_mobile(request, response):
        graph_render_config = graph_render_config.model_copy(
            update={
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

    if not available_metrics and perf_data and require_historic_metrics:
        return "", _(
            "No historic metrics recorded but metrics are available. "
            "Maybe metrics processing is disabled."
        )

    return "", render_graphs_from_specification_html(
        get_template_graph_specification(
            site_id=row["site"],
            host_name=row["host_name"],
            service_name=row.get("service_description", "_HOST_"),
        ),
        graph_data_range,
        graph_render_config,
        registered_metrics,
        registered_graphs,
        user_permissions,
        debug=debug,
        graph_timeranges=graph_timeranges,
        temperature_unit=temperature_unit,
        backend_time_series_fetcher=backend_time_series_fetcher,
        # Ideally, we would use 2-dim. coordinates: (row_idx, col_idx).
        # Unfortunately, we have no access to this information here. Regarding the rows, we could
        # use (site, host, service) as identifier, but for the columns, there does not seem to be
        # any unique information. The view rendering is designed st. individuals cells are rendered
        # completely independently of each other, based solely on the livestatus data and on the
        # painter settings (which makes sense). The caching in graph.ts breaks this assumption. So
        # for now, we randomize. See also CMK-13840.
        graph_display_id=str(uuid4()),
    )


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
        ("graph_render_options", vs_graph_render_options()),
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
    def ident(self) -> str:
        return "service_graphs"

    def title(self, cell: Cell) -> str:
        return _("Service graphs with time range previews")

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
        return ["pnp_timerange", "graph_render_options"]

    @property
    def parameters(self) -> MigrateNotUpdated:
        return cmk_time_graph_params()

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            metrics_from_api,
            graphs_from_api,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            user_permissions=self._user_permissions,
            debug=self.config.debug,
            graph_timeranges=self.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, self.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
            show_time_range_previews=True,
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError()


class PainterHostGraphs(Painter):
    @property
    def ident(self) -> str:
        return "host_graphs"

    def title(self, cell: Cell) -> str:
        return _("Host graphs with time range previews")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_perf_data", "host_metrics", "host_check_command"]

    @property
    def printable(self) -> str:
        return "time_graph"

    @property
    def painter_options(self) -> list[str]:
        return ["pnp_timerange", "graph_render_options"]

    @property
    def parameters(self) -> MigrateNotUpdated:
        return cmk_time_graph_params()

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            metrics_from_api,
            graphs_from_api,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            user_permissions=self._user_permissions,
            debug=self.config.debug,
            graph_timeranges=self.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, self.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
            show_time_range_previews=True,
            # for PainterHostGraphs used to paint service graphs (view "Service graphs of host"),
            # also render the graphs if there are no historic metrics available (but perf data is)
            require_historic_metrics="service_description" not in row,
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError()


class PainterOptionGraphRenderOptions(PainterOption):
    def __init__(self) -> None:
        super().__init__(ident="graph_render_options", valuespec=vs_graph_render_options())


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

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            metrics_from_api,
            graphs_from_api,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            user_permissions=self._user_permissions,
            debug=self.config.debug,
            graph_timeranges=self.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, self.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError()


class PainterHostPnpgraph(Painter):
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

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_time_graph_cmk(
            row,
            cell,
            metrics_from_api,
            graphs_from_api,
            user=user,
            request=self.request,
            response=response,
            painter_options=self._painter_options,
            user_permissions=self._user_permissions,
            debug=self.config.debug,
            graph_timeranges=self.config.graph_timeranges,
            temperature_unit=get_temperature_unit(user, self.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise PythonExportError()

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        raise JSONExportError()


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
