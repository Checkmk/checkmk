#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="redundant-expr"

from abc import ABC
from collections.abc import Sequence
from typing import Annotated, Literal, override, Self

from annotated_types import Ge, Interval, Unit
from pydantic import AfterValidator

from cmk.gui.dashboard.dashlet.dashlets.graph import (
    default_dashlet_graph_render_options,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.type_defs import (
    ABCGraphDashletConfig,
    CombinedGraphDashletConfig,
    CustomGraphDashletConfig,
    ProblemsGraphDashletConfig,
    SingleTimeseriesDashletConfig,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import (
    timerange_from_internal,
    TimerangeModel,
)
from cmk.gui.type_defs import GraphPresentation, GraphRenderOptionsVS, SizePT

from ..type_defs import ColorHex
from ._base import BaseWidgetContent


@api_model
class GraphRenderOptions:
    font_size_pt: Annotated[SizePT, Unit("pt")] | ApiOmitted = api_field(
        description="Font size in points.",
        default_factory=ApiOmitted,
    )
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
    color_gradient: Annotated[float, Interval(ge=0, le=100), Unit("%")] | ApiOmitted = api_field(
        description="Slight gradient in the colors of the colored areas in the graphs. 0% turns off the gradient, 100% makes it the strongest possible.",
        default_factory=ApiOmitted,
    )

    @staticmethod
    def _vertical_axis_width_from_internal(
        value: Literal["fixed"] | tuple[Literal["explicit"], SizePT] | None,
    ) -> Literal["fixed"] | SizePT | ApiOmitted:
        if value is None:
            return ApiOmitted()
        if isinstance(value, str) and value == "fixed":
            return "fixed"
        if isinstance(value, tuple) and value[0] == "explicit":
            return value[1]
        raise ValueError(f"Invalid vertical axis width: {value!r}")

    @classmethod
    def from_internal(cls, graph_render_options: GraphRenderOptionsVS) -> Self | ApiOmitted:
        if not graph_render_options:
            return ApiOmitted()

        return cls(
            font_size_pt=graph_render_options.get("font_size", ApiOmitted()),
            show_title=graph_render_options.get("show_title", ApiOmitted()),
            title_format=graph_render_options.get("title_format", ApiOmitted()),
            show_graph_time=graph_render_options.get("show_graph_time", ApiOmitted()),
            show_margin=graph_render_options.get("show_margin", ApiOmitted()),
            show_legend=graph_render_options.get("show_legend", ApiOmitted()),
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
            color_gradient=graph_render_options.get("color_gradient", ApiOmitted()),
        )

    def to_internal(self) -> GraphRenderOptionsVS:
        options = default_dashlet_graph_render_options()
        if not isinstance(self.font_size_pt, ApiOmitted):
            options["font_size"] = self.font_size_pt
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
        if not isinstance(self.color_gradient, ApiOmitted):
            options["color_gradient"] = self.color_gradient

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


def _only_str_on_input(_value: str) -> str:
    raise ValueError("Please use the graph ID instead of its number.")


@api_model
class PerformanceGraphContent(_BaseGraphContent):
    type: Literal["performance_graph"] = api_field(
        description="Displays a performance graph of a host or service."
    )
    # NOTE: we skip validation in case the value becomes invalid later
    source: str | Annotated[int, Ge(1), AfterValidator(_only_str_on_input)] = api_field(
        description="Graph id or number of the performance graph."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "pnpgraph"

    @classmethod
    def from_internal(cls, config: TemplateGraphDashletConfig) -> Self:
        return cls(
            type="performance_graph",
            timerange=timerange_from_internal(config.get("timerange", "25h")),
            graph_render_options=GraphRenderOptions.from_internal(
                config.get("graph_render_options", {})
            ),
            source=config["source"],
        )

    @override
    def to_internal(self) -> TemplateGraphDashletConfig:
        return TemplateGraphDashletConfig(
            **self._to_internal(),
            source=self.source,
        )
