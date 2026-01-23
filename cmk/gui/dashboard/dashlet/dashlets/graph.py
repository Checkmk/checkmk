#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Iterable, Mapping
from typing import Any, Generic, Literal, TypeVar

import livestatus

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_api
from cmk.gui import sites
from cmk.gui.config import active_config, Config
from cmk.gui.dashboard.type_defs import (
    ABCGraphDashletConfig,
    DashletSize,
)
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.graphing import (
    get_graph_plugin_and_single_metric_choices,
    get_graph_plugin_choices,
    get_metric_spec,
    get_temperature_unit,
    get_template_graph_specification,
    GraphDestinations,
    GraphPluginChoice,
    graphs_from_api,
    GraphSpecification,
    metrics_from_api,
    MKCombinedGraphLimitExceededError,
    MKGraphDashletTooSmallError,
    MKGraphRecipeCalculationError,
    MKGraphRecipeNotFoundError,
    RegisteredMetric,
    TemplateGraphSpecification,
    translated_metrics_from_row,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import (
    Choices,
    GraphRenderOptionsVS,
    SingleInfos,
    SizePT,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.valuespec import (
    DropdownChoiceWithHostAndServiceHints,
)
from cmk.gui.visuals import (
    get_only_sites_from_context,
    get_singlecontext_vars,
    livestatus_query_bare,
)
from cmk.utils.servicename import ServiceName

from ..base import Dashlet
from .status_helpers import make_mk_missing_data_error

GRAPH_TEMPLATE_CHOICE_AUTOCOMPLETER_ID = "available_graph_templates"


class AvailableGraphs(DropdownChoiceWithHostAndServiceHints):
    """Factory of a Dropdown menu from all graph templates"""

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
                ident=GRAPH_TEMPLATE_CHOICE_AUTOCOMPLETER_ID,
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
                    (c.id, c.title)
                    for c in get_graph_plugin_choices(graphs_from_api)
                    if c.id == value
                ),
                (
                    value,
                    (
                        _("Deprecated choice, please re-select")
                        if value == self._MARKER_DEPRECATED_CHOICE
                        else str(get_metric_spec(value, metrics_from_api).title)
                    ),
                ),
            )
        ]

    def render_input(self, varprefix: str, value: str | None) -> None:
        return super().render_input(
            varprefix,
            self._MARKER_DEPRECATED_CHOICE if isinstance(value, int) else value,
        )


T = TypeVar("T", bound=ABCGraphDashletConfig)
TGraphSpec = TypeVar("TGraphSpec", bound=GraphSpecification)


class ABCGraphDashlet(Dashlet[T], Generic[T, TGraphSpec]):
    @classmethod
    def initial_size(cls) -> DashletSize:
        return (60, 21)

    @classmethod
    def has_context(cls) -> bool:
        return True

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @staticmethod
    def _resolve_site(host: str) -> None:
        with sites.prepend_site():
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
            try:
                return sites.live().query_value(query)
            except livestatus.MKLivestatusNotFoundError:
                raise MKUserError("host", _("The host could not be found on any active site."))

    @abc.abstractmethod
    def build_graph_specification(self, context: VisualContext) -> TGraphSpec: ...

    def __init__(
        self,
        dashlet: T,
        base_context: VisualContext | None = None,
    ) -> None:
        super().__init__(dashlet=dashlet, base_context=base_context)

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        if "timerange" not in self._dashlet_spec:
            self._dashlet_spec["timerange"] = "25h"

        self._graph_specification: TGraphSpec | None = None
        self._graph_title: str | None = None
        self._init_exception: Exception | None = None
        try:
            self._graph_specification = self.build_graph_specification(
                self.context if self.has_context() else {}
            )
            self._graph_title = self._init_graph_title()
        except Exception as exc:
            # Passes error otherwise exception won't allow to enter dashlet editor
            self._init_exception = exc

    def graph_specification(self) -> TGraphSpec:
        if self._graph_specification is None:
            assert self._init_exception is not None
            raise self._init_exception

        return self._graph_specification

    def _init_graph_title(self) -> str | None:
        try:
            graph_recipes = self.graph_specification().recipes(
                metrics_from_api,
                graphs_from_api,
                UserPermissions.from_config(active_config, permission_registry),
                consolidation_function="max",
                debug=active_config.debug,
                temperature_unit=get_temperature_unit(user, active_config.default_temperature_unit),
            )
        except MKMissingDataError:
            raise
        except livestatus.MKLivestatusNotFoundError:
            raise make_mk_missing_data_error(reason=_("Service or host not found."))
        except (
            MKGraphRecipeCalculationError,
            MKGraphRecipeNotFoundError,
            MKGraphDashletTooSmallError,
        ):
            raise make_mk_missing_data_error()
        except MKCombinedGraphLimitExceededError as limit_exceeded_error:
            raise make_mk_missing_data_error(reason=str(limit_exceeded_error))
        except Exception:
            raise MKGeneralException(_("Failed to calculate a graph recipe."))

        return graph_recipes[0].title if graph_recipes else None

    def default_display_title(self) -> str:
        return self._graph_title if self._graph_title is not None else self.title()


class TemplateGraphDashletConfig(ABCGraphDashletConfig):
    source: str | int  # graph id or index (1-based) of the graph in the template


class TemplateGraphDashlet(ABCGraphDashlet[TemplateGraphDashletConfig, TemplateGraphSpecification]):
    """Dashlet for rendering a single performance graph"""

    @classmethod
    def type_name(cls) -> Literal["pnpgraph"]:
        return "pnpgraph"

    @classmethod
    def title(cls):
        return _("Time series graph")

    @classmethod
    def description(cls):
        return _("Displays a time series graph of a host or service.")

    @classmethod
    def sort_index(cls) -> int:
        return 20

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return ["host", "service"]

    def build_graph_specification(self, context: VisualContext) -> TemplateGraphSpecification:
        single_context = get_singlecontext_vars(context, self.single_infos())
        host = single_context.get("host")
        if not host:
            raise MKUserError("host", _("Missing needed host parameter."))

        host = HostName(host)

        service = single_context.get("service")
        if not service:
            service = "_HOST_"

        site = get_only_sites_from_context(context) or self._resolve_site(host)
        if isinstance(site, list):
            site_id: SiteId | None = SiteId("".join(site))
        else:
            site_id = site

        # source changed from int (n'th graph) to the graph id in 2.0.0b6, but we cannot transform this, so we have to
        # handle this here
        raw_source = self._dashlet_spec["source"]
        if isinstance(raw_source, int):
            return get_template_graph_specification(
                site_id=site_id,
                host_name=host,
                service_name=service,
                graph_index=raw_source - 1,
                destination=GraphDestinations.dashlet,
            )

        return get_template_graph_specification(
            site_id=site_id,
            host_name=host,
            service_name=service,
            graph_id=raw_source,
            destination=GraphDestinations.dashlet,
        )

    def _get_additional_macros(self) -> Mapping[str, str]:
        if self._graph_specification is None:
            return {}

        site = self._graph_specification.site
        return {"$SITE$": site} if site else {}

    @classmethod
    def get_additional_macro_names(cls) -> Iterable[str]:
        yield "$SITE$"


def default_dashlet_graph_render_options() -> GraphRenderOptionsVS:
    return GraphRenderOptionsVS(
        font_size=SizePT(8),
        show_graph_time=False,
        show_margin=False,
        show_legend=False,
        show_title=False,
        show_controls=False,
        resizable=False,
        show_time_range_previews=False,
    )


def graph_templates_autocompleter(
    config: Config, value_entered_by_user: str, params: dict
) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the
    completions_params to get the list of choices"""
    return _graph_templates_autocompleter_testable(
        value_entered_by_user=value_entered_by_user,
        params=params,
        registered_metrics=metrics_from_api,
        registered_graphs=graphs_from_api,
        debug=config.debug,
        temperature_unit=get_temperature_unit(user, config.default_temperature_unit),
    )


def _graph_templates_autocompleter_testable(
    *,
    value_entered_by_user: str,
    params: Mapping[str, Any],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> Choices:
    if not params.get("context") and params.get("show_independent_of_context") is True:
        return _sorted_matching_graph_template_choices(
            value_entered_by_user,
            get_graph_plugin_choices(registered_graphs),
        )

    graph_template_choices, single_metric_template_choices = (
        _graph_and_single_metric_templates_choices_for_context(
            params["context"],
            registered_metrics,
            registered_graphs,
            debug=debug,
            temperature_unit=temperature_unit,
        )
    )

    return _sorted_matching_graph_template_choices(
        value_entered_by_user,
        graph_template_choices,
    ) + _sorted_matching_graph_template_choices(
        value_entered_by_user,
        single_metric_template_choices,
    )


def _graph_and_single_metric_templates_choices_for_context(
    context: VisualContext,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> tuple[list[GraphPluginChoice], list[GraphPluginChoice]]:
    graph_template_choices: list[GraphPluginChoice] = []
    single_metric_template_choices: list[GraphPluginChoice] = []

    for row in livestatus_query_bare(
        "service",
        context,
        ["service_check_command", "service_perf_data", "service_metrics"],
    ):
        graph_template_choices_for_row, single_metric_template_choices_for_row = (
            get_graph_plugin_and_single_metric_choices(
                registered_metrics,
                registered_graphs,
                row["site"],
                HostName(context["host"]["host"]),
                ServiceName(context["service"]["service"]),
                translated_metrics_from_row(
                    row,
                    registered_metrics,
                    debug=debug,
                    temperature_unit=temperature_unit,
                ),
            )
        )
        graph_template_choices.extend(graph_template_choices_for_row)
        single_metric_template_choices.extend(single_metric_template_choices_for_row)

    return graph_template_choices, single_metric_template_choices


def _sorted_matching_graph_template_choices(
    value_entered_by_user: str,
    all_choices: Iterable[GraphPluginChoice],
) -> Choices:
    return [
        (graph_template_choice.id, graph_template_choice.title)
        for graph_template_choice in sorted(
            (
                graph_template_choice
                for graph_template_choice in all_choices
                if value_entered_by_user.lower() in graph_template_choice.id.lower()
                or value_entered_by_user.lower() in graph_template_choice.title.lower()
            ),
            key=lambda graph_template_choice: graph_template_choice.title,
        )
    ]
