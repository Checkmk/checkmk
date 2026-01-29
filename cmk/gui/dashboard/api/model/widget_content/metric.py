#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="redundant-expr"

from abc import ABC
from typing import Annotated, assert_never, cast, Literal, override, Self

from pydantic import Discriminator

from cmk.gui.dashboard.type_defs import (
    AverageScatterplotDashletConfig,
    BarplotDashletConfig,
    GaugeDashletConfig,
    MetricDisplayRangeFixed,
    MetricDisplayRangeWithAutomatic,
    MetricTimeRange,
    MetricTimeRangeParameters,
    SingleGraphDashletConfig,
    StatusDisplayWithText,
    TopListColumnConfig,
    TopListDashletConfig,
)
from cmk.gui.graphing import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    id_from_unit_spec,
    metrics_from_api,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal, TimerangeModel
from cmk.gui.unit_formatter import AutoPrecision

from ..type_defs import ColorHex
from ._base import BaseWidgetContent


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
        if metric := metrics_from_api.get(metric_name):
            unit_spec = metric.unit_spec
        else:
            unit_spec = ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol=""),
                precision=AutoPrecision(digits=2),
            )
        return "fixed", (id_from_unit_spec(unit_spec), (self.minimum, self.maximum))


type MetricDisplayRangeModel = Literal["automatic"] | MetricDisplayRangeFixedModel


def _metric_display_range_from_internal(
    value: MetricDisplayRangeWithAutomatic,
) -> MetricDisplayRangeModel:
    if value == "automatic":
        return "automatic"
    if isinstance(value, tuple) and value[0] == "fixed":
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


@api_model
class MetricTimeRangeWindow:
    type: Literal["window"] = api_field(description="Select values over a range of time.")
    window: TimerangeModel = api_field(description="Time range to select values from.")
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
    def from_internal(cls, config: MetricTimeRangeParameters) -> Self:
        return cls(
            type="window",
            window=timerange_from_internal(config["window"]),
            consolidation=cls.consolidation_from_internal(config["rrd_consolidation"]),
        )

    def to_internal(self) -> MetricTimeRangeParameters:
        return {
            "window": self.window.to_internal(),
            "rrd_consolidation": self.consolidation_to_internal(),
        }


type MetricTimeRangeModel = Literal["current"] | MetricTimeRangeWindow


def _metric_time_range_from_internal(value: MetricTimeRange) -> MetricTimeRangeModel:
    match value:
        case "current":
            return "current"
        case ("range", config):
            return MetricTimeRangeWindow.from_internal(config)
    # TODO: change to `assert_never` once mypy can handle it correctly
    raise ValueError(f"Invalid metric time range: {value!r}")


def _metric_time_range_to_internal(value: MetricTimeRangeModel) -> MetricTimeRange:
    match value:
        case "current":
            return "current"
        case MetricTimeRangeWindow():
            return "range", value.to_internal()
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
            # mypy can't handle type narrowing here
            return MetricStatusDisplayText(type="text", for_states=cast(ForStates, for_states))
        case ("background", for_states):
            # mypy can't handle type narrowing here
            return MetricStatusDisplayBackground(
                type="background", for_states=cast(ForStates, for_states)
            )
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
        )

    @override
    def to_internal(self) -> BarplotDashletConfig:
        return BarplotDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            display_range=_metric_display_range_to_internal(self.metric, self.display_range),
        )


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
        )


type DefaultOrColor = Literal["default"] | ColorHex


@api_model
class AverageScatterplotContent(_BaseMetricContent):
    type: Literal["average_scatterplot"] = api_field(
        description="Display a scatterplot of average values over time.",
    )
    time_range: TimerangeModel = api_field(description="Time range to select values from.")
    metric_color: DefaultOrColor = api_field(description="Color of the scattered dots.")
    average_color: DefaultOrColor = api_field(description="Color of the average.")
    median_color: DefaultOrColor = api_field(description="Color of the median.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "average_scatterplot"

    @classmethod
    def from_internal(cls, config: AverageScatterplotDashletConfig) -> Self:
        return cls(
            type="average_scatterplot",
            metric=config["metric"],
            time_range=timerange_from_internal(config["time_range"]),
            metric_color=config.get("metric_color") or "default",
            average_color=config.get("avg_color") or "default",
            median_color=config.get("median_color") or "default",
        )

    @override
    def to_internal(self) -> AverageScatterplotDashletConfig:
        return AverageScatterplotDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            time_range=self.time_range.to_internal(),
            metric_color=self.metric_color,
            avg_color=self.average_color,
            median_color=self.median_color,
        )


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
        )

    @override
    def to_internal(self) -> TopListDashletConfig:
        return TopListDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            columns=self.columns.to_internal(),
            display_range=_metric_display_range_to_internal(self.metric, self.display_range),
            ranking_order=self.ranking_order,
            limit_to=self.limit_to,
        )
