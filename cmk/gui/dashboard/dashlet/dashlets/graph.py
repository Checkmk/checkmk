#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal, NotRequired, override

import cmk.livestatus_client as livestatus
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import ConsolidationFunction, TimeRange
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui import sites
from cmk.gui.config import active_config, Config
from cmk.gui.dashboard.exceptions import WidgetRenderError
from cmk.gui.dashboard.type_defs import ABCGraphDashletConfig
from cmk.gui.exceptions import MKUserError
from cmk.gui.graphing import (
    build_template_graphs,
    discover_template_graphs,
    evaluate_built_graphs,
    get_graph_plugin_choices,
    get_metric_spec,
    get_template_graph_specification,
    graph_choices,
    GraphChoices,
    GraphDestinations,
    GraphFromAPI,
    GraphPluginChoice,
    graphs_from_api,
    GraphSpecification,
    metrics_from_api,
    registered_metrics,
    registered_translations,
    resolve_graph_id_from_index,
    RRDFetchMetricNames,
    sort_registered_graph_plugins,
    TemplateGraphSpecification,
)
from cmk.gui.graphing._engine_discovery import DiscoveredGraphs
from cmk.gui.i18n import _
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import (
    Choices,
    GraphRenderOptionsVS,
    SingleInfos,
    SizePT,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import (
    DropdownChoiceWithHostAndServiceHints,
    Timerange,
)
from cmk.gui.visuals import (
    get_only_sites_from_context,
    get_singlecontext_vars,
)
from cmk.utils.servicename import ServiceName
from cmk.web.utils.autocompleter_config import ContextAutocompleterConfig

from ..base import (
    Dashlet,
    RelativeLayoutConstraints,
    ResponsiveLayoutConstraints,
    WidgetSize,
)

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

    @override
    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if not value or value == self._MARKER_DEPRECATED_CHOICE:
            raise MKUserError(varprefix, _("Please select a graph."))

    @override
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

    @override
    def render_input(self, varprefix: str, value: str | None) -> None:
        return super().render_input(
            varprefix,
            self._MARKER_DEPRECATED_CHOICE if isinstance(value, int) else value,  # type: ignore[redundant-expr]
        )


class ABCGraphDashlet[T: ABCGraphDashletConfig, TGraphSpec: GraphSpecification](Dashlet[T]):
    @classmethod
    @override
    def has_context(cls) -> bool:
        return True

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=60, height=21))

    @classmethod
    @override
    def responsive_layout_constraints(cls) -> ResponsiveLayoutConstraints:
        return ResponsiveLayoutConstraints.large_default()

    @override
    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @staticmethod
    def _resolve_site(host: str) -> None:
        with sites.prepend_site():
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host)
            try:
                return sites.live().query_value(query)
            except livestatus.MKLivestatusNotFoundError:
                raise WidgetRenderError(
                    _("The host '%(host)s' could not be found on any active site.")
                    % {"host": host},
                )

    @abc.abstractmethod
    def build_graph_specification(self, context: VisualContext) -> TGraphSpec: ...

    @abc.abstractmethod
    def discover_graphs(
        self, *, debug: bool, user_permissions: UserPermissions
    ) -> DiscoveredGraphs:
        """The data-less engine graphs this widget renders.

        The client-side graph widgets fetch their data for these definitions; the server-side
        rendering path goes through `recipes` instead. Only the graph specification is needed
        here, so a widget whose legacy recipes cannot be computed still resolves its graphs.

        What discovery needs of the configuration is passed in rather than read from the active
        config, so the token-authenticated fetch can supply it from the API context.
        """

    def __init__(
        self,
        dashlet: T,
        base_context: VisualContext | None = None,
    ) -> None:
        super().__init__(dashlet=dashlet, base_context=base_context)

        # New graphs which have been added via "add to visual" option don't have a timerange
        # configured. So we assume the default timerange here by default.
        # TODO: If the comment above is correct, the typing is wrong => suppression for now
        if "timerange" not in self._dashlet_spec:
            self._dashlet_spec["timerange"] = "25h"  # type: ignore[unreachable]

        self._graph_resolved = False
        self._cached_graph_specification: TGraphSpec | None = None
        self._resolve_exception: Exception | None = None
        self._cached_display_title: str | None = None

    def _resolve_graph(self) -> None:
        """Build the specification once, recording rather than raising a failure."""
        if self._graph_resolved:
            return
        self._graph_resolved = True
        try:
            self._cached_graph_specification = self.build_graph_specification(
                self.context if self.has_context() else {}
            )
        except Exception as e:
            self._resolve_exception = e

    def graph_specification(self) -> TGraphSpec | None:
        """The resolved specification, or None when it could not be built."""
        self._resolve_graph()
        return self._cached_graph_specification

    @override
    def default_display_title(self) -> str:
        # TODO: This evaluates the graph only to substitute a title expression. Move the macro
        # resolution to the frontend, or give the engine a performance-data-only fetch for titles.
        if self._cached_display_title is None:
            self._cached_display_title = self._resolve_display_title()
        return self._cached_display_title

    def _resolve_display_title(self) -> str:
        try:
            start, end = Timerange.compute_range(self._dashlet_spec["timerange"]).range
            discovered = self.discover_graphs(
                debug=active_config.debug,
                user_permissions=UserPermissions.from_config(active_config, permission_registry),
            )
            evaluated = evaluate_built_graphs(
                [built.graph for built in discovered.graphs[:1]],
                {
                    "consolidation_function": ConsolidationFunction.MAX,
                    "time_range": TimeRange(start=int(start), end=int(end), step=60),
                    "destination": None,
                },
            )
        except Exception:
            return self.title()
        return evaluated.graphs[0].title if evaluated.graphs else self.title()


class TemplateGraphDashletConfig(ABCGraphDashletConfig):
    # Legacy 1-based graph index. Present only in pre-CMK-7308 configs.
    source: NotRequired[int]
    # Stable graph id. Written by all new configs.
    graph_id: NotRequired[str]


class TemplateGraphDashlet(ABCGraphDashlet[TemplateGraphDashletConfig, TemplateGraphSpecification]):
    """Dashlet for rendering a single performance graph"""

    @classmethod
    @override
    def type_name(cls) -> Literal["pnpgraph"]:
        return "pnpgraph"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Time series graph")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays a time series graph of a host or service.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 20

    @classmethod
    @override
    def single_infos(cls) -> SingleInfos:
        return ["host", "service"]

    @override
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

        # New configs carry the stable ``graph_id``; pre-CMK-7308 dashlets stored the 1-based graph
        # index in ``source``. Resolve the legacy int to a stable id at this boundary.
        configured_graph_id = self._dashlet_spec.get("graph_id")
        legacy_source = self._dashlet_spec.get("source")
        if configured_graph_id is not None:
            graph_id: str | None = configured_graph_id
        elif legacy_source is not None:
            graph_id = resolve_graph_id_from_index(
                site_id=site_id,
                host_name=host,
                service_name=service,
                graph_index=legacy_source - 1,
                debug=active_config.debug,
            )
        else:
            graph_id = None

        return get_template_graph_specification(
            site_id=site_id,
            host_name=host,
            service_name=service,
            graph_id=graph_id,
            destination=GraphDestinations.dashlet,
        )

    @override
    def discover_graphs(
        self, *, debug: bool, user_permissions: UserPermissions
    ) -> DiscoveredGraphs:
        if (graph_specification := self.graph_specification()) is None:
            assert self._resolve_exception is not None
            raise self._resolve_exception
        return discover_template_graphs(graph_specification, debug=debug)

    @override
    def _get_additional_macros(self) -> Mapping[str, str]:
        if (graph_specification := self.graph_specification()) is None:
            return {}

        site = graph_specification.site
        return {"$SITE$": site} if site else {}

    @classmethod
    @override
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
        registered_plugin_graphs=graphs_from_api,
        registered_metric_definitions=registered_metrics(),
        registered_translations=registered_translations(),
        debug=config.debug,
    )


def _graph_templates_autocompleter_testable(
    *,
    value_entered_by_user: str,
    params: Mapping[str, Any],
    registered_plugin_graphs: Mapping[str, GraphFromAPI],
    registered_metric_definitions: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    debug: bool,
) -> Choices:
    if not params.get("context") and params.get("show_independent_of_context") is True:
        return _sorted_matching_graph_template_choices(
            value_entered_by_user,
            get_graph_plugin_choices(registered_plugin_graphs),
        )

    choices = _graph_and_single_metric_templates_choices_for_context(
        params["context"],
        registered_plugin_graphs,
        registered_metric_definitions,
        registered_translations,
        debug=debug,
    )
    return _sorted_matching_graph_template_choices(
        value_entered_by_user,
        choices.plugin_graphs,
    ) + _sorted_matching_graph_template_choices(
        value_entered_by_user,
        choices.single_metrics,
    )


def _graph_and_single_metric_templates_choices_for_context(
    context: VisualContext,
    registered_graphs: Mapping[str, GraphFromAPI],
    registered_metric_definitions: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    *,
    debug: bool,
) -> GraphChoices:
    if "host" not in context or "service" not in context:
        return GraphChoices(plugin_graphs=[], single_metrics=[])

    only_sites = get_only_sites_from_context(context)
    site_id = only_sites[0] if only_sites and len(only_sites) == 1 else None
    host_name = HostName(context["host"]["host"])
    service_name = ServiceName(context["service"]["service"])
    sorted_graph_plugins = [
        plugin for _name, plugin in sort_registered_graph_plugins(registered_graphs)
    ]
    return graph_choices(
        [
            built.graph
            for built in build_template_graphs(
                get_template_graph_specification(
                    site_id=site_id,
                    host_name=host_name,
                    service_name=service_name,
                ),
                registered_graphs=sorted_graph_plugins,
                registered_metrics=registered_metric_definitions,
                fetch_metric_names=RRDFetchMetricNames(
                    host_name=EngineHostName(host_name),
                    service_name=EngineServiceName(service_name),
                    debug=debug,
                    site_id=site_id,
                    registered_translations=registered_translations,
                ),
            )
        ],
        sorted_graph_plugins,
    )


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
