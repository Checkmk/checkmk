#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from itertools import chain
from typing import Any, Dict, Iterable, Mapping
from typing import Tuple as TupleType

import livestatus

from cmk.utils.macros import MacroMapping
from cmk.utils.type_defs import MetricName

import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.exceptions import MKGeneralException, MKMissingDataError, MKUserError
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.metrics import (
    get_graph_templates,
    graph_info,
    metric_info,
    translated_metrics_from_row,
)
from cmk.gui.plugins.dashboard import Dashlet, dashlet_registry
from cmk.gui.plugins.dashboard.utils import (
    DashboardConfig,
    DashboardName,
    DashletConfig,
    DashletId,
    macro_mapping_from_context,
    make_mk_missing_data_error,
)
from cmk.gui.plugins.metrics.html_render import (
    default_dashlet_graph_render_options,
    resolve_graph_recipe,
)
from cmk.gui.plugins.visuals.utils import livestatus_query_bare
from cmk.gui.plugins.metrics.valuespecs import vs_graph_render_options
from cmk.gui.type_defs import Choices, GraphIdentifier, VisualContext
from cmk.gui.valuespec import (
    Dictionary,
    DictionaryElements,
    DictionaryEntry,
    DropdownChoice,
    DropdownChoiceValue,
    DropdownChoiceWithHostAndServiceHints,
    ValueSpec,
    autocompleter_registry,
)


def _metric_title_from_id(metric_or_graph_id: MetricName) -> str:
    metric_id = metric_or_graph_id.replace("METRIC_", "")
    return metric_info.get(metric_id, {}).get("title", metric_id)


# Sneak CMK 2.1 autocompleter endpoints to make the 2.0 connector usable on CMK 2.0 too.
def _graph_choices_from_livestatus_row(row) -> Iterable[TupleType[str, str]]:
    def _graph_template_title(graph_template: Mapping) -> str:
        return str(graph_template.get("title", "")) or _metric_title_from_id(graph_template["id"])

    yield from ((
        template["id"],
        _graph_template_title(template),
    ) for template in get_graph_templates(translated_metrics_from_row(row)))


def graph_templates_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the
    completions_params to get the list of choices"""
    if not params.get("context") and params.get("strict", "False") == "False":
        choices: Iterable[TupleType[str, str]] = ((
            graph_id,
            str(graph_details.get(
                "title",
                graph_id,
            )),
        ) for graph_id, graph_details in graph_info.items())

    else:
        columns = [
            "service_check_command",
            "service_perf_data",
            "service_metrics",
        ]

        choices = set(
            chain.from_iterable(
                _graph_choices_from_livestatus_row(row)
                for row in livestatus_query_bare("service", params["context"], columns)))

    return sorted((v for v in choices if value.lower() in v[1].lower()), key=lambda a: a[1].lower())


@autocompleter_registry.register
class AvailableGraphs(DropdownChoiceWithHostAndServiceHints):
    """Factory of a Dropdown menu from all graph templates"""
    ident = "available_graphs"
    _MARKER_DEPRECATED_CHOICE = "_deprecated_int_value"

    def __init__(self, **kwargs: Any):
        kwargs_with_defaults: Mapping[str, Any] = {
            "css_spec": ["ajax-vals", "graph-selector", self.ident],
            "hint_label": _("graph"),
            "choices": [(None, _("Select graph"))],
            "title": _("Graph"),
            "help": _(
                "Select the graph to be displayed by this element. In case the current selection "
                "displays 'Deprecated choice, please re-select', this element was created before "
                "the release of version 2.0. Before this version, the graph selection was based on "
                "a single number indexing the output of the corresponding service. Such elements "
                "will continue to work, however, if you want to re-edit them, you have to re-"
                "select the graph. To check which graph is currently selected, look at the title "
                "of the element in the dashboard.",),
            **kwargs,
        }
        super().__init__(**kwargs_with_defaults)

    def _validate_value(
        self,
        value: DropdownChoiceValue,
        varprefix: str,
    ) -> None:
        if not value or value == self._MARKER_DEPRECATED_CHOICE:
            raise MKUserError(varprefix, _("Please select a graph."))

    def _choices_from_value(self, value: DropdownChoiceValue) -> Choices:
        if not value:
            return self.choices()
        return [
            next(
                ((
                    graph_id,
                    graph_detail.get(
                        "title",
                        graph_id,
                    ),
                ) for graph_id, graph_detail in graph_info.items() if graph_id == value),
                (
                    value,
                    _("Deprecated choice, please re-select")
                    if value == self._MARKER_DEPRECATED_CHOICE else _metric_title_from_id(value),
                ),
            )
        ]

    def render_input(self, varprefix: str, value: DropdownChoiceValue) -> None:
        return super().render_input(
            varprefix,
            self._MARKER_DEPRECATED_CHOICE if isinstance(value, int) else value,
        )

    @staticmethod
    def _graph_template_title(graph_template: Mapping) -> str:
        return graph_template.get("title") or _metric_title_from_id(graph_template["id"])

    @classmethod
    def _graph_choices_from_livestatus_row(
        cls,
        perf_data: str,
        metrics: Iterable[MetricName],
        check_cmd: str,
    ) -> Iterable[TupleType[str, str]]:
        yield from ((
            template["id"],
            cls._graph_template_title(template),
        ) for template in get_graph_templates(
            translated_metrics_from_row({
                "service_metrics": metrics,
                "service_perf_data": perf_data,
                "service_check_command": check_cmd,
            })))

    # This class in to use them Text autocompletion ajax handler. Valuespec is not used on html
    @classmethod
    def autocomplete_choices(cls, value: str, params: Dict) -> Choices:
        """Return the matching list of dropdown choices
        Called by the webservice with the current input field value and the
        completions_params to get the list of choices"""

        # Sneak CMK 2.1 autocompleter endpoints to make the 2.0 connector usable on CMK 2.0 too.
        if "context" in params:
            return graph_templates_autocompleter(value, params)

        if not (params.get("host") or params.get("service")):
            choices: Iterable[TupleType[str, str]] = ((
                graph_id,
                graph_details.get(
                    "title",
                    graph_id,
                ),
            ) for graph_id, graph_details in graph_info.items())

        else:
            query = "\n".join([
                "GET services",
                "Columns: perf_data metrics check_command",
            ] + [
                f"Filter: {filter_name} = {livestatus.lqencode(filter_value)}"
                for filter_name, filter_value in (
                    ("host_name", params.get("host")),
                    ("service_description", params.get("service")),
                )
                if filter_value
            ])
            with sites.set_limit(None):
                choices = set(
                    chain.from_iterable(
                        cls._graph_choices_from_livestatus_row(
                            perf_data,
                            metrics,
                            check_cmd,
                        ) for perf_data, metrics, check_cmd in sites.live().query(query)))

        val_lower = value.lower()
        return sorted(
            (choice for choice in choices if val_lower in choice[1].lower()),
            key=lambda tuple_id_title: tuple_id_title[1],
        )


@dashlet_registry.register
class GraphDashlet(Dashlet):
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
    def sort_index(cls):
        return 20

    @classmethod
    def initial_refresh_interval(cls):
        return 60

    @classmethod
    def initial_size(cls):
        return (60, 21)

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return ["host", "service"]

    @classmethod
    def has_context(cls):
        return True

    def default_display_title(self) -> str:
        return self._dashlet_spec.get("_graph_title") or self.title()

    def __init__(self, dashboard_name: DashboardName, dashboard: DashboardConfig,
                 dashlet_id: DashletId, dashlet: DashletConfig) -> None:
        super().__init__(dashboard_name=dashboard_name,
                         dashboard=dashboard,
                         dashlet_id=dashlet_id,
                         dashlet=dashlet)

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        self._dashlet_spec.setdefault('timerange', '1')

        self._init_exception = None
        try:
            self._init_graph()
        except Exception as exc:
            # Passes error otherwise exception wont allow to enter dashlet editor
            self._init_exception = exc

    def _init_graph(self):
        context = visuals.get_merged_context(
            visuals.get_context_from_uri_vars(["host", "service"], self.single_infos()),
            self._dashlet_spec["context"])
        self._dashlet_spec["_graph_identification"] = self.graph_identification(context)

        try:
            graph_recipes = resolve_graph_recipe(self._dashlet_spec["_graph_identification"])
        except MKMissingDataError:
            raise
        except livestatus.MKLivestatusNotFoundError:
            raise make_mk_missing_data_error()
        except Exception:
            raise MKGeneralException(_("Failed to calculate a graph recipe."))

        self._dashlet_spec["_graph_title"] = graph_recipes[0]["title"]

    @staticmethod
    def _resolve_site(host):
        # When the site is available via URL context, use it. Otherwise it is needed
        # to check all sites for the requested host
        if html.request.has_var('site'):
            return html.request.var('site')

        with sites.prepend_site():
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
            try:
                return sites.live().query_value(query)
            except livestatus.MKLivestatusNotFoundError:
                raise MKUserError("host", _("The host could not be found on any active site."))

    def graph_identification(self, context: VisualContext) -> GraphIdentifier:
        host = context.get("host")
        if not host:
            raise MKUserError('host', _('Missing needed host parameter.'))

        service = context.get("service")
        if not service:
            service = "_HOST_"

        site = self._resolve_site(host)

        # source changed from int (n'th graph) to the graph id in 2.0.0b6, but we cannot transform this, so we have to
        # handle this here
        raw_source = self._dashlet_spec["source"]
        if isinstance(raw_source, int):
            graph_def = {"graph_index": raw_source - 1}
        else:
            graph_def = {"graph_id": raw_source}

        return (
            "template",
            {
                "site": site,
                "host_name": host,
                "service_description": service,
                **graph_def,
            },
        )

    @classmethod
    def vs_parameters(cls) -> ValueSpec:
        return Dictionary(
            title=_('Properties'),
            render='form',
            optional_keys=[],
            elements=cls._parameter_elements,
        )

    @staticmethod
    def _vs_timerange() -> DictionaryEntry:
        # TODO: Cleanup: switch to generic Timerange() valuespec!
        return (
            "timerange",
            DropdownChoice(
                title=_('Timerange'),
                default_value='1',
                choices=[
                    ("0", _("4 Hours")),
                    ("1", _("25 Hours")),
                    ("2", _("One Week")),
                    ("3", _("One Month")),
                    ("4", _("One Year")),
                ],
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

    @classmethod
    def _parameter_elements(cls) -> DictionaryElements:
        yield cls._vs_timerange()
        yield (
            "source",
            AvailableGraphs(),
        )
        yield cls._vs_graph_render_options()

    @classmethod
    def script(cls):
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
                  + "&timerange=" + encodeURIComponent(timerange)
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

    def on_resize(self):
        return self._reload_js()

    def on_refresh(self):
        return self._reload_js()

    def _reload_js(self):
        if any(prop not in self._dashlet_spec
               for prop in ["_graph_identification", "graph_render_options", "timerange"]):
            return ""

        return "dashboard_render_graph(%d, %s, %s, '%s')" % (
            self._dashlet_id,
            json.dumps(self._dashlet_spec["_graph_identification"]),
            json.dumps(self._dashlet_spec["graph_render_options"]),
            self._dashlet_spec['timerange'],
        )

    def show(self):
        if self._init_exception:
            raise self._init_exception

        html.div("", id_="dashlet_graph_%d" % self._dashlet_id)

    def _get_macro_mapping(self, title: str) -> MacroMapping:
        macro_mapping = macro_mapping_from_context(
            self.context,
            self.single_infos(),
            self.display_title(),
            self.default_display_title(),
            **self._get_additional_macros(),
        )
        return macro_mapping

    def _get_additional_macros(self) -> Mapping[str, str]:
        try:
            site = self.dashlet_spec["_graph_identification"][1].get("site")
        except KeyError:
            return {}
        return {"$SITE$": site} if site else {}

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield "$SITE$"
