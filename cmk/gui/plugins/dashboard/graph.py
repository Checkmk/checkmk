#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
from typing import Any, Generic, Iterable, Mapping, TypeVar

import livestatus

from cmk.utils.macros import MacroMapping
from cmk.utils.type_defs import MetricName

import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException, MKMissingDataError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import (
    ABCGraphDashletConfig,
    DashboardConfig,
    DashboardName,
    Dashlet,
    dashlet_registry,
    DashletId,
    DashletSize,
    macro_mapping_from_context,
    make_mk_missing_data_error,
)
from cmk.gui.plugins.metrics.html_render import (
    default_dashlet_graph_render_options,
    resolve_graph_recipe,
)
from cmk.gui.plugins.metrics.utils import graph_info, metric_info
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options
from cmk.gui.plugins.visuals.utils import get_only_sites_from_context
from cmk.gui.type_defs import (
    Choices,
    GraphIdentifier,
    SingleInfos,
    TemplateGraphIdentifier,
    TemplateGraphSpec,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.valuespec import (
    Dictionary,
    DictionaryElements,
    DictionaryEntry,
    DropdownChoiceWithHostAndServiceHints,
    Timerange,
    ValueSpec,
)
from cmk.gui.visuals import get_singlecontext_vars


def _metric_title_from_id(metric_or_graph_id: MetricName) -> str:
    metric_id = metric_or_graph_id.replace("METRIC_", "")
    return str(metric_info.get(metric_id, {}).get("title", metric_id))


class AvailableGraphs(DropdownChoiceWithHostAndServiceHints):
    """Factory of a Dropdown menu from all graph templates"""

    ident = "available_graphs"
    _MARKER_DEPRECATED_CHOICE = "_deprecated_int_value"

    def __init__(self, **kwargs: Any) -> None:
        kwargs_with_defaults: Mapping[str, Any] = {
            "css_spec": ["ajax-vals"],
            "hint_label": _("graph"),
            "title": _("Graph"),
            "help": _(
                "Select the graph to be displayed by this element. In case the current selection "
                "displays 'Deprecated choice, please re-select', this element was created before "
                "the release of version 2.0. Before this version, the graph selection was based on "
                "a single number indexing the output of the corresponding service. Such elements "
                "will continue to work, however, if you want to re-edit them, you have to re-"
                "select the graph. To check which graph is currently selected, look at the title "
                "of the element in the dashboard.",
            ),
            "autocompleter": ContextAutocompleterConfig(
                ident=self.ident,
                strict=True,
                show_independent_of_context=True,
                dynamic_params_callback_name="host_and_service_hinted_autocompleter",
            ),
            **kwargs,
        }
        super().__init__(**kwargs_with_defaults)

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if not value or value == self._MARKER_DEPRECATED_CHOICE:
            raise MKUserError(varprefix, _("Please select a graph."))

    def _choices_from_value(self, value: str | None) -> Choices:
        if not value:
            return list(self.choices())
        return [
            next(
                (
                    (
                        graph_id,
                        str(
                            graph_detail.get(
                                "title",
                                graph_id,
                            )
                        ),
                    )
                    for graph_id, graph_detail in graph_info.items()
                    if graph_id == value
                ),
                (
                    value,
                    _("Deprecated choice, please re-select")
                    if value == self._MARKER_DEPRECATED_CHOICE
                    else _metric_title_from_id(value),
                ),
            )
        ]

    def render_input(self, varprefix: str, value: str | None) -> None:
        return super().render_input(
            varprefix,
            self._MARKER_DEPRECATED_CHOICE if isinstance(value, int) else value,
        )


T = TypeVar("T", bound=ABCGraphDashletConfig)
T_Ident = TypeVar("T_Ident", bound=GraphIdentifier)


class ABCGraphDashlet(Dashlet[T], Generic[T, T_Ident]):
    @classmethod
    def initial_size(cls) -> DashletSize:
        return (60, 21)

    @classmethod
    def initial_refresh_interval(cls) -> int:
        return 60

    @classmethod
    def has_context(cls) -> bool:
        return True

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    def vs_parameters(cls) -> ValueSpec:
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=[],
            elements=cls._parameter_elements,
        )

    @classmethod
    def _parameter_elements(cls) -> DictionaryElements:
        yield cls._vs_timerange()
        yield cls._vs_graph_render_options()

    @staticmethod
    def _vs_timerange() -> DictionaryEntry:
        return (
            "timerange",
            Timerange(
                title=_("Timerange"),
                default_value="25h",
            ),
        )

    @staticmethod
    def _vs_graph_render_options() -> DictionaryEntry:
        return (
            "graph_render_options",
            vs_graph_render_options(
                default_values=default_dashlet_graph_render_options,
                exclude=[
                    "show_time_range_previews",
                    "title_format",
                    "show_title",
                ],
            ),
        )

    @staticmethod
    def _resolve_site(host: str) -> None:
        with sites.prepend_site():
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
            try:
                return sites.live().query_value(query)
            except livestatus.MKLivestatusNotFoundError:
                raise MKUserError("host", _("The host could not be found on any active site."))

    @classmethod
    def script(cls) -> str:
        return """
var dashlet_offsets = {};
function dashboard_render_graph(nr, graph_identification, graph_render_options, timerange)
{
    // Get the target size for the graph from the inner dashlet container
    var inner = document.getElementById('dashlet_inner_' + nr);
    var c_w = inner.clientWidth;
    var c_h = inner.clientHeight;

    var post_data = "spec=" + encodeURIComponent(JSON.stringify(graph_identification))
                  + "&render=" + encodeURIComponent(JSON.stringify(graph_render_options))
                  + "&timerange=" + encodeURIComponent(JSON.stringify(timerange))
                  + "&width=" + c_w
                  + "&height=" + c_h
                  + "&id=" + nr;

    cmk.ajax.call_ajax("graph_dashlet.py", {
        post_data        : post_data,
        method           : "POST",
        response_handler : handle_dashboard_render_graph_response,
        handler_data     : nr,
    });
}

function handle_dashboard_render_graph_response(handler_data, response_body)
{
    var nr = handler_data;
    var container = document.getElementById('dashlet_graph_' + nr);
    if (container) {
        container.innerHTML = response_body;
        cmk.utils.execute_javascript_by_object(container);
    }
}

"""

    @abc.abstractmethod
    def graph_identification(self, context: VisualContext) -> T_Ident:
        ...

    def __init__(
        self,
        dashboard_name: DashboardName,
        dashboard: DashboardConfig,
        dashlet_id: DashletId,
        dashlet: T,
    ) -> None:
        super().__init__(
            dashboard_name=dashboard_name,
            dashboard=dashboard,
            dashlet_id=dashlet_id,
            dashlet=dashlet,
        )

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        if "timerange" not in self._dashlet_spec:
            self._dashlet_spec["timerange"] = "25h"

        self._graph_identification: T_Ident | None = None
        self._graph_title: str | None = None
        self._init_exception = None
        try:
            self._graph_identification, self._graph_title = self._init_graph()
        except Exception as exc:
            # Passes error otherwise exception wont allow to enter dashlet editor
            self._init_exception = exc

    def _init_graph(self) -> tuple[T_Ident, str | None]:
        graph_identification = self.graph_identification(self.context if self.has_context() else {})

        try:
            graph_recipes = resolve_graph_recipe(graph_identification)
        except MKMissingDataError:
            raise
        except livestatus.MKLivestatusNotFoundError:
            raise make_mk_missing_data_error()
        except MKUserError as e:
            raise MKGeneralException(_("Failed to calculate a graph recipe. (%s)") % str(e))
        except Exception:
            raise MKGeneralException(_("Failed to calculate a graph recipe."))

        graph_title = graph_recipes[0]["title"] if graph_recipes else None

        return graph_identification, graph_title

    def default_display_title(self) -> str:
        return self._graph_title if self._graph_title is not None else self.title()

    def on_resize(self) -> str:
        return self._reload_js()

    def on_refresh(self) -> str:
        return self._reload_js()

    def _reload_js(self) -> str:
        if self._graph_identification is None or self._graph_title is None:
            return ""

        return "dashboard_render_graph(%d, %s, %s, %s)" % (
            self._dashlet_id,
            json.dumps(self._graph_identification),
            json.dumps(self._dashlet_spec["graph_render_options"]),
            json.dumps(self._dashlet_spec["timerange"]),
        )

    def show(self) -> None:
        if self._init_exception:
            raise self._init_exception

        html.div("", id_="dashlet_graph_%d" % self._dashlet_id)

    def _get_macro_mapping(self, title: str) -> MacroMapping:
        macro_mapping = macro_mapping_from_context(
            self.context if self.has_context() else {},
            self.single_infos(),
            self.display_title(),
            self.default_display_title(),
            **self._get_additional_macros(),
        )
        return macro_mapping

    def _get_additional_macros(self) -> Mapping[str, str]:
        return {}

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from []


class TemplateGraphDashletConfig(ABCGraphDashletConfig):
    source: str


@dashlet_registry.register
class TemplateGraphDashlet(ABCGraphDashlet[TemplateGraphDashletConfig, TemplateGraphIdentifier]):
    """Dashlet for rendering a single performance graph"""

    @classmethod
    def type_name(cls):
        return "pnpgraph"

    @classmethod
    def title(cls):
        return _("Performance graph")

    @classmethod
    def description(cls):
        return _("Displays a performance graph of a host or service.")

    @classmethod
    def sort_index(cls) -> int:
        return 20

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return ["host", "service"]

    def graph_identification(self, context: VisualContext) -> TemplateGraphIdentifier:
        single_context = get_singlecontext_vars(context, self.single_infos())
        host = single_context.get("host")
        if not host:
            raise MKUserError("host", _("Missing needed host parameter."))

        service = single_context.get("service")
        if not service:
            service = "_HOST_"

        site = get_only_sites_from_context(context) or self._resolve_site(host)
        if isinstance(site, list):
            site_id: str | None = "".join(site)
        else:
            site_id = site

        # source changed from int (n'th graph) to the graph id in 2.0.0b6, but we cannot transform this, so we have to
        # handle this here
        raw_source = self._dashlet_spec["source"]
        if isinstance(raw_source, int):
            graph_spec = TemplateGraphSpec(
                {
                    "site": site_id,
                    "host_name": host,
                    "service_description": service,
                    "graph_index": raw_source - 1,
                }
            )
        else:
            graph_spec = TemplateGraphSpec(
                {
                    "site": site_id,
                    "host_name": host,
                    "service_description": service,
                    "graph_id": raw_source,
                }
            )

        return ("template", graph_spec)

    @classmethod
    def _parameter_elements(cls) -> DictionaryElements:
        yield (
            "source",
            AvailableGraphs(),
        )
        yield from super()._parameter_elements()

    def _get_additional_macros(self) -> Mapping[str, str]:
        if self._graph_identification is None:
            return {}

        site = self._graph_identification[1].get("site")
        return {"$SITE$": site} if site else {}

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield "$SITE$"
