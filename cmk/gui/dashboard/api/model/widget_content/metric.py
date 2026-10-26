#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import ABC
from typing import Annotated, assert_never, Literal, override, Self

from pydantic import Discriminator

from cmk.graphing_engine import metric_attributes
from cmk.gui.dashboard.type_defs import (
    AverageScatterplotDashletConfig,
    BarplotDashletConfig,
    GaugeDashletConfig,
    MetricCurrentValue,
    MetricDashboardWindow,
    MetricDisplayRangeFixed,
    MetricDisplayRangeWithAutomatic,
    MetricFixedWindow,
    MetricTimeRange,
    SingleGraphDashletConfig,
    SingleMetricSparkHeightMode,
    StatusDisplayWithText,
    TopListColumnConfig,
    TopListDashletConfig,
)
from cmk.gui.graphing import id_from_unit, registered_metrics
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import (
    ColorHex,
    timerange_from_internal,
    TimerangeModel,
)
from cmk.gui.type_defs import GraphLegendStyle

from ..context_filters import (
    OBJECT_HOST_FILTER_ADAPTER,
    OBJECT_SERVICE_FILTER_ADAPTER,
    ObjectHostContextFilter,
    ObjectServiceContextFilter,
)
from ..contextual_link import (
    AnyContextualLinkSpec,
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLinkSpec,
)
from ._base import BaseWidgetContent, time_range_from_internal, time_range_to_internal


# TODO: Reimplement/Investigate a validation function for this class MetricDisplayRangeFixedModel
#       See ticket CMK-26644.
@api_model
class MetricDisplayRangeFixedModel:
    type: Literal["fixed"] = api_field(description="Display a fixed range of values.")
    unit: str = api_field(description="Unit for the range")
    minimum: int | float = api_field(description="Minimum value of the range.")
    maximum: int | float = api_field(description="Maximum value of the range.")

    def __post_init__(self) -> None:
        if self.minimum >= self.maximum:
            raise ValueError("Minimum must be less than maximum")

    @staticmethod
    def _unit_symbol_from_internal(value: str) -> str:
        full_format = value.split("_")
        if len(full_format) == 4:
            _notation, symbol, _precision, _digits = full_format
            return symbol
        if len(full_format) == 1:
            # this seems to only come up for some builtin dashboards with % ranges
            # the UI updates the unit to these default values when the user edits the widget
            return value
        raise ValueError(f"Invalid unit format: {value!r}")

    @classmethod
    def from_internal(cls, value: MetricDisplayRangeFixed) -> Self:
        _, (unit, (minimum, maximum)) = value
        return cls(
            type="fixed",
            unit=cls._unit_symbol_from_internal(unit),
            minimum=minimum,
            maximum=maximum,
        )

    def to_internal(self, metric_name: str) -> MetricDisplayRangeFixed:
        unit = metric_attributes(
            metric_name, translate_to_current_language, registered_metrics()
        ).unit
        return "fixed", (id_from_unit(unit), (self.minimum, self.maximum))


type MetricDisplayRangeModel = Literal["automatic"] | MetricDisplayRangeFixedModel


def _metric_display_range_from_internal(
    value: MetricDisplayRangeWithAutomatic,
) -> MetricDisplayRangeModel:
    if value == "automatic":
        return "automatic"
    if value[0] == "fixed":
        _, (unit, (minimum, maximum)) = value
        return MetricDisplayRangeFixedModel(
            type="fixed",
            unit=unit,
            minimum=minimum,
            maximum=maximum,
        )
    assert_never(value)


def _metric_display_range_to_internal(
    metric_name: str,
    value: MetricDisplayRangeModel,
) -> MetricDisplayRangeWithAutomatic:
    match value:
        case "automatic":
            return "automatic"
        case MetricDisplayRangeFixedModel():
            return value.to_internal(metric_name)
    assert_never(value)


type MetricWindowModel = Literal["dashboard"] | TimerangeModel


@api_model
class MetricTimeRangeWindow:
    type: Literal["window"] = api_field(description="Select values over a range of time.")
    window: MetricWindowModel = api_field(
        description="Time range to select values from, or `dashboard` to follow the dashboard."
    )
    consolidation: Literal["average", "minimum", "maximum"] = api_field(
        description="How to consolidate the values over the time range.",
    )

    @classmethod
    def consolidation_from_internal(
        cls, value: Literal["average", "min", "max"]
    ) -> Literal["average", "minimum", "maximum"]:
        match value:
            case "average":
                return "average"
            case "min":
                return "minimum"
            case "max":
                return "maximum"
        assert_never(value)

    def consolidation_to_internal(self) -> Literal["average", "min", "max"]:
        match self.consolidation:
            case "average":
                return "average"
            case "minimum":
                return "min"
            case "maximum":
                return "max"
        assert_never(self.consolidation)

    @classmethod
    def from_internal(cls, config: MetricFixedWindow | MetricDashboardWindow) -> Self:
        return cls(
            type="window",
            window=(
                "dashboard"
                if config["type"] == "dashboard"
                else timerange_from_internal(config["window"])
            ),
            consolidation=cls.consolidation_from_internal(config["rrd_consolidation"]),
        )

    def to_internal(self) -> MetricFixedWindow | MetricDashboardWindow:
        consolidation = self.consolidation_to_internal()
        if self.window == "dashboard":
            return MetricDashboardWindow(type="dashboard", rrd_consolidation=consolidation)
        return MetricFixedWindow(
            type="range", window=self.window.to_internal(), rrd_consolidation=consolidation
        )


type MetricTimeRangeModel = Literal["current"] | MetricTimeRangeWindow


def _metric_time_range_from_internal(value: MetricTimeRange) -> MetricTimeRangeModel:
    if value["type"] == "current":
        return "current"
    return MetricTimeRangeWindow.from_internal(value)


def _metric_time_range_to_internal(value: MetricTimeRangeModel) -> MetricTimeRange:
    match value:
        case "current":
            return MetricCurrentValue(type="current")
        case MetricTimeRangeWindow():
            return value.to_internal()
    # TODO: change to `assert_never` once mypy can handle it correctly
    raise ValueError(f"Invalid metric time range: {value!r}")


type ForStates = Literal["all", "not_ok"]


@api_model
class MetricStatusDisplayText:
    type: Literal["text"] = api_field(
        description="Show a colored status label.",
    )
    for_states: ForStates = api_field(description="Which states to show the status label for.")


@api_model
class MetricStatusDisplayBackground:
    type: Literal["background"] = api_field(
        description="Show a colored status label and color the metric background.",
    )
    for_states: ForStates = api_field(description="Which states to show the status label for.")


type MetricStatusDisplayModel = Annotated[
    MetricStatusDisplayText | MetricStatusDisplayBackground, Discriminator("type")
]


def _metric_status_display_from_internal(
    value: StatusDisplayWithText,
) -> MetricStatusDisplayModel | ApiOmitted:
    match value:
        case None:
            return ApiOmitted()
        case ("text", for_states):
            return MetricStatusDisplayText(type="text", for_states=for_states)
        case ("background", for_states):
            return MetricStatusDisplayBackground(type="background", for_states=for_states)
    # TODO: change to `assert_never` once mypy can handle it correctly
    raise ValueError(f"Invalid metric status display: {value!r}")


def _metric_status_display_to_internal(
    value: MetricStatusDisplayModel | ApiOmitted,
) -> StatusDisplayWithText:
    match value:
        case ApiOmitted():
            return None
        case MetricStatusDisplayText():
            return value.type, value.for_states
        case MetricStatusDisplayBackground():
            return value.type, value.for_states
    assert_never(value)


@api_model
class _BaseMetricContent(BaseWidgetContent, ABC):
    # NOTE: we skip validation in case the value becomes invalid later
    metric: str = api_field(description="Name of the metric.")


@api_model
class BarplotContent(_BaseMetricContent):
    type: Literal["barplot"] = api_field(description="Display a single metric as a barplot.")
    display_range: MetricDisplayRangeModel = api_field(description="Range of values to display.")
    contextual_link: ContextualLinkSpec[ObjectServiceContextFilter] = api_field(
        description="Where a click on a bar leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "barplot"

    @classmethod
    def from_internal(cls, config: BarplotDashletConfig) -> Self:
        return cls(
            type="barplot",
            metric=config["metric"],
            display_range=_metric_display_range_from_internal(config["display_range"]),
            contextual_link=contextual_link_from_internal(
                config.get("contextual_link"), OBJECT_SERVICE_FILTER_ADAPTER
            ),
        )

    @override
    def to_internal(self) -> BarplotDashletConfig:
        config = BarplotDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            display_range=_metric_display_range_to_internal(self.metric, self.display_range),
        )
        if (link := contextual_link_to_internal(self.contextual_link)) is not None:
            config["contextual_link"] = link
        return config

    @override
    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        return self.contextual_link


@api_model
class GaugeContent(_BaseMetricContent):
    type: Literal["gauge"] = api_field(description="Display a single value as a gauge.")
    time_range: MetricTimeRangeModel = api_field(description="Time range to select values from.")
    display_range: MetricDisplayRangeFixedModel = api_field(
        description="Range of values to display.",
    )
    status_display: MetricStatusDisplayModel | ApiOmitted = api_field(
        description="Display the service status.",
        default_factory=ApiOmitted,
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "gauge"

    @classmethod
    def from_internal(cls, config: GaugeDashletConfig) -> Self:
        return cls(
            type="gauge",
            metric=config["metric"],
            display_range=MetricDisplayRangeFixedModel.from_internal(config["display_range"]),
            time_range=_metric_time_range_from_internal(config["time_range"]),
            status_display=_metric_status_display_from_internal(config["status_display"]),
        )

    @override
    def to_internal(self) -> GaugeDashletConfig:
        return GaugeDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            display_range=self.display_range.to_internal(self.metric),
            time_range=_metric_time_range_to_internal(self.time_range),
            status_display=_metric_status_display_to_internal(self.status_display),
        )


@api_model
class SingleMetricContent(_BaseMetricContent):
    type: Literal["single_metric"] = api_field(
        description="Displays a single metric of a specific host and service.",
    )
    time_range: MetricTimeRangeModel = api_field(description="Time range to select values from.")
    status_display: MetricStatusDisplayModel | ApiOmitted = api_field(
        description="Display the service status.",
        default_factory=ApiOmitted,
    )
    display_range: MetricDisplayRangeModel = api_field(description="Range of values to display.")
    show_display_range_limits: bool = api_field(
        description="Display axis labels for the selected/automatic data range.",
    )
    spark_height_mode: SingleMetricSparkHeightMode | ApiOmitted = api_field(
        description="Whether the sparkline runs the full height of the card, behind the "
        "value, or as a band strictly below it.",
        default_factory=ApiOmitted,
    )
    show_delta: bool = api_field(
        description="Whether to show the change versus the average of the displayed window."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "single_metric"

    @classmethod
    def from_internal(cls, config: SingleGraphDashletConfig) -> Self:
        return cls(
            type="single_metric",
            metric=config["metric"],
            time_range=_metric_time_range_from_internal(config["time_range"]),
            status_display=_metric_status_display_from_internal(config["status_display"]),
            display_range=_metric_display_range_from_internal(config["display_range"]),
            show_display_range_limits=config["toggle_range_display"],
            spark_height_mode=config.get("spark_height_mode", "full"),
            show_delta=config.get("show_delta", True),
        )

    @override
    def to_internal(self) -> SingleGraphDashletConfig:
        return SingleGraphDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            time_range=_metric_time_range_to_internal(self.time_range),
            status_display=_metric_status_display_to_internal(self.status_display),
            display_range=_metric_display_range_to_internal(self.metric, self.display_range),
            toggle_range_display=self.show_display_range_limits,
            spark_height_mode=(
                "full" if isinstance(self.spark_height_mode, ApiOmitted) else self.spark_height_mode
            ),
            show_delta=self.show_delta,
        )


type DefaultOrColor = Literal["default"] | ColorHex


@api_model
class AverageScatterplotContent(_BaseMetricContent):
    type: Literal["average_scatterplot"] = api_field(
        description="Display a scatterplot of average values over time.",
    )
    time_range: Literal["dashboard"] | TimerangeModel = api_field(
        description="Time range to select values from, or `dashboard` to follow the dashboard.",
    )
    metric_color: DefaultOrColor = api_field(description="Color of the scattered dots.")
    average_color: DefaultOrColor = api_field(description="Color of the average.")
    median_color: DefaultOrColor = api_field(description="Color of the median.")
    show_legend: bool | ApiOmitted = api_field(
        description="Show the graph legend. Defaults to false.",
        default_factory=ApiOmitted,
    )
    legend_style: GraphLegendStyle | ApiOmitted = api_field(
        description="How the legend is drawn when show_legend is set: compact names the series in "
        "a single row, extended lists them in a table with their statistics. Defaults to compact.",
        default_factory=ApiOmitted,
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "average_scatterplot"

    @classmethod
    def from_internal(cls, config: AverageScatterplotDashletConfig) -> Self:
        return cls(
            type="average_scatterplot",
            metric=config["metric"],
            time_range=time_range_from_internal(config["time_range"]),
            metric_color=config.get("metric_color") or "default",
            average_color=config.get("avg_color") or "default",
            median_color=config.get("median_color") or "default",
            show_legend=config.get("show_legend", ApiOmitted()),
            legend_style=config.get("legend_style", ApiOmitted()),
        )

    @override
    def to_internal(self) -> AverageScatterplotDashletConfig:
        config = AverageScatterplotDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            time_range=time_range_to_internal(self.time_range),
            metric_color=self.metric_color,
            avg_color=self.average_color,
            median_color=self.median_color,
        )
        if not isinstance(self.show_legend, ApiOmitted):
            config["show_legend"] = self.show_legend
        if not isinstance(self.legend_style, ApiOmitted):
            config["legend_style"] = self.legend_style
        return config


@api_model
class TopListColumns:
    show_service_description: bool = api_field(
        description="Show the service description in the top list.",
    )
    show_bar_visualization: bool = api_field(
        description="Show a bar visualization for the metric values in the top list.",
    )

    @classmethod
    def from_internal(cls, config: TopListColumnConfig) -> Self:
        return cls(
            show_service_description=config.get("show_service_description", False),
            show_bar_visualization=config.get("show_bar_visualization", False),
        )

    def to_internal(self) -> TopListColumnConfig:
        config = TopListColumnConfig()
        if self.show_service_description:
            config["show_service_description"] = True
        if self.show_bar_visualization:
            config["show_bar_visualization"] = True
        return config


@api_model
class TopListContent(_BaseMetricContent):
    type: Literal["top_list"] = api_field(description="Display a list of top metrics.")
    columns: TopListColumns = api_field(description="Columns to display in the top list.")
    display_range: MetricDisplayRangeModel = api_field(description="Range of values to display.")
    ranking_order: Literal["high", "low"] = api_field(
        description="Display highest or lowest values."
    )
    limit_to: int = api_field(description="Limit the number of entries in the top list.")
    # Host filters only: both cells name the row's host, but the host cell names no service.
    contextual_link: ContextualLinkSpec[ObjectHostContextFilter] = api_field(
        description="Where a click on a host or service name leads."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "top_list"

    @classmethod
    def from_internal(cls, config: TopListDashletConfig) -> Self:
        return cls(
            type="top_list",
            metric=config["metric"],
            columns=TopListColumns.from_internal(config["columns"]),
            display_range=_metric_display_range_from_internal(config["display_range"]),
            ranking_order=config["ranking_order"],
            limit_to=config["limit_to"],
            contextual_link=contextual_link_from_internal(
                config.get("contextual_link"), OBJECT_HOST_FILTER_ADAPTER
            ),
        )

    @override
    def to_internal(self) -> TopListDashletConfig:
        config = TopListDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            columns=self.columns.to_internal(),
            display_range=_metric_display_range_to_internal(self.metric, self.display_range),
            ranking_order=self.ranking_order,
            limit_to=self.limit_to,
        )
        if (link := contextual_link_to_internal(self.contextual_link)) is not None:
            config["contextual_link"] = link
        return config

    @override
    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        return self.contextual_link
