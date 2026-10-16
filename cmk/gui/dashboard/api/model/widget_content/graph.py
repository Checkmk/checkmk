#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC
from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, cast, Literal, override, Protocol, runtime_checkable, Self

from annotated_types import Ge, Unit
from pydantic import GetCoreSchemaHandler, WithJsonSchema
from pydantic_core import core_schema, CoreSchema, ErrorDetails

from cmk.gui.dashboard import dashlet_registry
from cmk.gui.dashboard.dashlet.dashlets.graph import (
    default_dashlet_graph_render_options,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.type_defs import (
    ABCGraphDashletConfig,
    CombinedGraphDashletConfig,
    CustomGraphDashletConfig,
    DashletConfig,
    EmbeddedCustomGraphDashletConfig,
    ProblemsGraphDashletConfig,
    SingleTimeseriesDashletConfig,
)
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import (
    ColorHex,
    timerange_from_internal,
    TimerangeModel,
)
from cmk.gui.type_defs import (
    DashboardEmbeddedViewSpec,
    GraphLegendStyle,
    GraphPresentation,
    GraphRenderOptionsVS,
    SizePT,
    VerticalAxisWidth,
)

from ._base import BaseWidgetContent


@api_model
class GraphRenderOptions:
    show_title: bool | Literal["inline"] | ApiOmitted = api_field(
        description="Whether to show the title of the graph.",
        default_factory=ApiOmitted,
    )
    title_format: (
        Sequence[Literal["plain", "add_host_name", "add_host_alias", "add_service_description"]]
        | ApiOmitted
    ) = api_field(
        description="Format of the graph title.",
        default_factory=ApiOmitted,
    )
    show_graph_time: bool | ApiOmitted = api_field(
        description="Show the graph time range on top of the graph.",
        default_factory=ApiOmitted,
    )
    show_margin: bool | ApiOmitted = api_field(
        description="Show the margin around the graph.",
        default_factory=ApiOmitted,
    )
    show_legend: bool | ApiOmitted = api_field(
        description="Show the graph legend.",
        default_factory=ApiOmitted,
    )
    legend_style: GraphLegendStyle | ApiOmitted = api_field(
        description="How the legend is drawn when show_legend is set: compact names the series in "
        "a single row, extended lists them in a table with their statistics. Defaults to compact.",
        default_factory=ApiOmitted,
    )
    show_vertical_axis: bool | ApiOmitted = api_field(
        description="Show the graph vertical axis.",
        default_factory=ApiOmitted,
    )
    vertical_axis_width: Literal["fixed"] | Annotated[SizePT, Unit("pt")] | ApiOmitted = api_field(
        description="Width of the vertical axis.",
        default_factory=ApiOmitted,
    )
    show_time_axis: bool | ApiOmitted = api_field(
        description="Show the graph time axis.",
        default_factory=ApiOmitted,
    )
    show_controls: bool | ApiOmitted = api_field(
        description="Show the graph controls.",
        default_factory=ApiOmitted,
    )
    show_pin: bool | ApiOmitted = api_field(
        description="Show the pin.",
        default_factory=ApiOmitted,
    )
    show_time_range_previews: bool | ApiOmitted = api_field(
        description="Show time range previews.",
        default_factory=ApiOmitted,
    )
    fixed_timerange: bool | ApiOmitted = api_field(
        description="Do not follow timerange changes of other graphs on the current page.",
        default_factory=ApiOmitted,
    )
    border_width_mm: Annotated[float, Unit("mm")] | ApiOmitted = api_field(
        description="Width of the black border around the whole graph, in millimeters. Enter 0 for no border here.",
        default_factory=ApiOmitted,
    )

    @staticmethod
    def _vertical_axis_width_from_internal(
        value: VerticalAxisWidth | None,
    ) -> Literal["fixed"] | SizePT | ApiOmitted:
        if value is None:
            return ApiOmitted()
        if isinstance(value, str) and value == "fixed":
            return "fixed"
        if value[0] == "explicit":
            return value[1]
        raise ValueError(f"Invalid vertical axis width: {value!r}")

    @classmethod
    def from_internal(cls, graph_render_options: GraphRenderOptionsVS) -> Self | ApiOmitted:
        if not graph_render_options:
            return ApiOmitted()

        return cls(
            show_title=graph_render_options.get("show_title", ApiOmitted()),
            title_format=graph_render_options.get("title_format", ApiOmitted()),
            show_graph_time=graph_render_options.get("show_graph_time", ApiOmitted()),
            show_margin=graph_render_options.get("show_margin", ApiOmitted()),
            show_legend=graph_render_options.get("show_legend", ApiOmitted()),
            legend_style=graph_render_options.get("legend_style", ApiOmitted()),
            show_vertical_axis=graph_render_options.get("show_vertical_axis", ApiOmitted()),
            vertical_axis_width=cls._vertical_axis_width_from_internal(
                graph_render_options.get("vertical_axis_width"),
            ),
            show_time_axis=graph_render_options.get("show_time_axis", ApiOmitted()),
            show_controls=graph_render_options.get("show_controls", ApiOmitted()),
            show_pin=graph_render_options.get("show_pin", ApiOmitted()),
            show_time_range_previews=graph_render_options.get(
                "show_time_range_previews", ApiOmitted()
            ),
            fixed_timerange=graph_render_options.get("fixed_timerange", ApiOmitted()),
            border_width_mm=graph_render_options.get("border_width", ApiOmitted()),
        )

    def to_internal(self) -> GraphRenderOptionsVS:
        options = default_dashlet_graph_render_options()
        if not isinstance(self.show_title, ApiOmitted):
            # Transform "inline" to "inline", otherwise pass bool
            options["show_title"] = self.show_title
        if not isinstance(self.title_format, ApiOmitted):
            options["title_format"] = self.title_format
        if not isinstance(self.show_graph_time, ApiOmitted):
            options["show_graph_time"] = self.show_graph_time
        if not isinstance(self.show_margin, ApiOmitted):
            options["show_margin"] = self.show_margin
        if not isinstance(self.show_legend, ApiOmitted):
            options["show_legend"] = self.show_legend
        if not isinstance(self.legend_style, ApiOmitted):
            options["legend_style"] = self.legend_style
        if not isinstance(self.show_vertical_axis, ApiOmitted):
            options["show_vertical_axis"] = self.show_vertical_axis
        if not isinstance(self.vertical_axis_width, ApiOmitted):
            if self.vertical_axis_width == "fixed":
                options["vertical_axis_width"] = "fixed"
            else:
                options["vertical_axis_width"] = "explicit", self.vertical_axis_width
        if not isinstance(self.show_time_axis, ApiOmitted):
            options["show_time_axis"] = self.show_time_axis
        if not isinstance(self.show_controls, ApiOmitted):
            options["show_controls"] = self.show_controls
        if not isinstance(self.show_pin, ApiOmitted):
            options["show_pin"] = self.show_pin
        if not isinstance(self.show_time_range_previews, ApiOmitted):
            options["show_time_range_previews"] = self.show_time_range_previews
        if not isinstance(self.fixed_timerange, ApiOmitted):
            options["fixed_timerange"] = self.fixed_timerange
        if not isinstance(self.border_width_mm, ApiOmitted):
            options["border_width"] = self.border_width_mm

        return options


@api_model
class _BaseGraphContent(BaseWidgetContent, ABC):
    timerange: TimerangeModel = api_field(
        description="The time range for the graph, e.g. '25h' for last 25 hours.",
    )
    graph_render_options: GraphRenderOptions | ApiOmitted = api_field(
        description="Graph render options",
        default_factory=ApiOmitted,
    )

    def _get_graph_render_options_internal(self) -> GraphRenderOptionsVS:
        if isinstance(self.graph_render_options, ApiOmitted):
            return default_dashlet_graph_render_options()

        return self.graph_render_options.to_internal()

    def _to_internal(self) -> ABCGraphDashletConfig:
        return ABCGraphDashletConfig(
            type=self.internal_type(),
            timerange=self.timerange.to_internal(),
            graph_render_options=self._get_graph_render_options_internal(),
        )


@api_model
class ProblemGraphContent(_BaseGraphContent):
    type: Literal["problem_graph"] = api_field(
        description=(
            "Shows the percentage of services that are not OK in relation to the total "
            "number of services. This widget is not respecting the full filter context "
            "of the dashboard, only the 'site' filter."
        ),
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "problem_graph"

    @classmethod
    def from_internal(cls, config: ProblemsGraphDashletConfig) -> Self:
        return cls(
            type="problem_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
        )

    @override
    def to_internal(self) -> ProblemsGraphDashletConfig:
        return ProblemsGraphDashletConfig(**self._to_internal())


@api_model
class CombinedGraphContent(_BaseGraphContent):
    type: Literal["combined_graph"] = api_field(description="Displays a combined graph")
    # NOTE: we skip validation in case the value becomes invalid later
    graph_template: str = api_field(
        description="The graph template to use for the combined graph.",
    )
    presentation: GraphPresentation = api_field(description="The format of the combined graph.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "combined_graph"

    @classmethod
    def from_internal(cls, config: CombinedGraphDashletConfig) -> Self:
        return cls(
            type="combined_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            graph_template=config["graph_template"],
            presentation=config["presentation"],
        )

    @override
    def to_internal(self) -> CombinedGraphDashletConfig:
        return CombinedGraphDashletConfig(
            **self._to_internal(),
            graph_template=self.graph_template,
            presentation=self.presentation,
        )


@api_model
class SingleTimeseriesContent(_BaseGraphContent):
    type: Literal["single_timeseries"] = api_field(
        description="Displays a timeseries for a single metric of a specific host and service.",
    )
    # NOTE: we skip validation in case the value becomes invalid later
    metric: str = api_field(description="Name of the metric.")
    color: Literal["default_theme", "default_metric"] | ColorHex = api_field(
        description="Color of the timeseries line.",
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "single_timeseries"

    @classmethod
    def from_internal(cls, config: SingleTimeseriesDashletConfig) -> Self:
        return cls(
            type="single_timeseries",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            metric=config["metric"],
            color=config["color"],
        )

    @override
    def to_internal(self) -> SingleTimeseriesDashletConfig:
        return SingleTimeseriesDashletConfig(
            **self._to_internal(),
            metric=self.metric,
            color=self.color,
        )


@api_model
class CustomGraphContent(_BaseGraphContent):
    type: Literal["custom_graph"] = api_field(
        description="Displays a custom graph designed with the graph designer.",
    )
    # NOTE: we skip validation in case the value becomes invalid later
    custom_graph: str = api_field(description="Name of the custom graph.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "custom_graph"

    @classmethod
    def from_internal(cls, config: CustomGraphDashletConfig) -> Self:
        return cls(
            type="custom_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            custom_graph=config["custom_graph"],
        )

    @override
    def to_internal(self) -> CustomGraphDashletConfig:
        # NOTE: mypy doesn't like missing non-required fields in ** expressions
        #       so we can't use **self._to_internal() here
        return CustomGraphDashletConfig(
            type=self.internal_type(),
            timerange=self.timerange.to_internal(),
            graph_render_options=self._get_graph_render_options_internal(),
            custom_graph=self.custom_graph,
        )


@runtime_checkable
class EmbeddedCustomGraphHandler[D](Protocol):
    """What the content model needs of the widget registered for embedded custom graphs.
    The definition schema lives in nonfree code, so the widget provides it structurally."""

    @classmethod
    def definition_model(cls) -> type[D]:
        """The API model of the definition; pydantic validates the field with it."""

    @classmethod
    def definition_to_internal(cls, definition: D) -> dict[str, object]:
        """API model (CustomGraphDefinition) to stored shape (CustomGraphContentV2)."""

    @classmethod
    def definition_from_internal(cls, stored: Mapping[str, object]) -> D:
        """Stored shape to API model."""

    @classmethod
    def iter_definition_errors(
        cls,
        definition: D,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        stored_definition: Mapping[str, object] | None,
    ) -> Iterable[ErrorDetails]:
        """Data source errors of the definition, and its telemetry errors unless it is unchanged
        from `stored_definition`, located below `location`."""


def _embedded_custom_graph_handler() -> type[EmbeddedCustomGraphHandler[object]] | None:
    internal_type = EmbeddedCustomGraphContent.internal_type()
    if internal_type in dashlet_registry and issubclass(
        handler := dashlet_registry[internal_type], EmbeddedCustomGraphHandler
    ):
        return handler
    return None


class _DefinitionSchema:
    """The registered widget's model validates the field; without one it stays a plain dict.

    Resolved when pydantic builds the schema, which the REST API does lazily and caches per
    process, after all editions registered their widgets."""

    def __get_pydantic_core_schema__(
        self, source: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        if (widget := _embedded_custom_graph_handler()) is None:
            return core_schema.dict_schema(core_schema.str_schema(), core_schema.any_schema())
        return handler.generate_schema(widget.definition_model())


@api_model
class EmbeddedCustomGraphContent(_BaseGraphContent):
    type: Literal["embedded_custom_graph"] = api_field(
        description="Displays a custom graph whose definition is stored in the widget.",
    )
    # the JSON schema keeps the API the same for all editions
    definition: Annotated[
        object,
        _DefinitionSchema(),
        WithJsonSchema({"type": "object", "additionalProperties": True, "title": "Definition"}),
    ] = api_field(
        description=(
            "The graph options and data sources of the graph, in the shape of the "
            "CustomGraphDefinition of the custom graph API."
        ),
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "embedded_custom_graph"

    @classmethod
    def from_internal(cls, config: EmbeddedCustomGraphDashletConfig) -> Self:
        handler = _embedded_custom_graph_handler()
        return cls(
            type="embedded_custom_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            # without a handler (edition downgrade) the widget cannot render its stored definition,
            # and saving it is rejected, so an empty one keeps the dashboard readable
            definition=(
                {} if handler is None else handler.definition_from_internal(config["definition"])
            ),
        )

    @override
    def to_internal(self) -> EmbeddedCustomGraphDashletConfig:
        if (handler := _embedded_custom_graph_handler()) is None:
            raise ValueError("Widget is not supported by this edition")
        return EmbeddedCustomGraphDashletConfig(
            type=self.internal_type(),
            timerange=self.timerange.to_internal(),
            graph_render_options=self._get_graph_render_options_internal(),
            definition=handler.definition_to_internal(self.definition),
        )

    @override
    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],
        stored_widget: DashletConfig | None,
    ) -> Iterable[ErrorDetails]:
        if (handler := _embedded_custom_graph_handler()) is None:
            return
        # a definition the save leaves as stored was checked for its author, and the writer may
        # lack the telemetry permission the author had
        yield from handler.iter_definition_errors(
            self.definition,
            location + ("definition",),
            context,
            stored_definition=(
                cast(EmbeddedCustomGraphDashletConfig, stored_widget)["definition"]
                if stored_widget is not None and stored_widget["type"] == self.internal_type()
                else None
            ),
        )


@api_model
class PerformanceGraphContent(_BaseGraphContent):
    type: Literal["performance_graph"] = api_field(
        description="Displays a performance graph of a host or service."
    )
    # NOTE: we skip validation in case the value becomes invalid later
    source: str | Annotated[int, Ge(1)] = api_field(
        description="Graph id or number of the performance graph."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "pnpgraph"

    @classmethod
    def from_internal(cls, config: TemplateGraphDashletConfig) -> Self:
        # Prefer the new stable ``graph_id`` field; fall back to the legacy ``source`` index for
        # pre-CMK-7308 dashboards.
        graph_id = config.get("graph_id")
        source: str | int
        if graph_id is not None:
            source = graph_id
        else:
            legacy_source = config.get("source")
            assert legacy_source is not None
            source = legacy_source
        return cls(
            type="performance_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            source=source,
        )

    @override
    def to_internal(self) -> TemplateGraphDashletConfig:
        # The REST API still exposes a single ``source`` field; route string ids into the new
        # ``graph_id`` field and keep int indices in the legacy ``source`` field.
        # NOTE: mypy doesn't like missing non-required fields in ** expressions,
        #       so we can't use **self._to_internal() here.
        if isinstance(self.source, int):
            return TemplateGraphDashletConfig(
                type=self.internal_type(),
                timerange=self.timerange.to_internal(),
                graph_render_options=self._get_graph_render_options_internal(),
                source=self.source,
            )
        return TemplateGraphDashletConfig(
            type=self.internal_type(),
            timerange=self.timerange.to_internal(),
            graph_render_options=self._get_graph_render_options_internal(),
            graph_id=self.source,
        )
