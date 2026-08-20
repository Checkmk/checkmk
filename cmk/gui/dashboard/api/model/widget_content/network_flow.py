#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, override, Self

from cmk.gui.dashboard.type_defs import (
    NetworkFlowAccent,
    NetworkFlowDonutDashletConfig,
    NetworkFlowDonutDimension,
    NetworkFlowDonutLegendMode,
    NetworkFlowKpiStatCardDashletConfig,
    NetworkFlowKpiStatCardMetric,
    NetworkFlowTopTableDashletConfig,
    NetworkFlowTopTableDimension,
    NetworkFlowTrendChartDashletConfig,
    NetworkFlowTrendChartDimension,
    NetworkFlowTrendChartDisplayMode,
)
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent


@api_model
class NetworkFlowTopTableContent(BaseWidgetContent):
    type: Literal["network_flow_top_table"] = api_field(
        description="Displays top-N network flow entities ranked by volume with inline bars."
    )
    dimension: NetworkFlowTopTableDimension = api_field(
        description="Which entity dimension to rank (local hosts, remote hosts, applications "
        "or autonomous systems)."
    )
    accent: NetworkFlowAccent = api_field(description="Accent color of the inline bars.")
    limit_to: int = api_field(description="Maximum number of rows to display.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "network_flow_top_table"

    @classmethod
    def from_internal(cls, config: NetworkFlowTopTableDashletConfig) -> Self:
        return cls(
            type="network_flow_top_table",
            dimension=config["dimension"],
            accent=config["accent"],
            limit_to=config["limit_to"],
        )

    @override
    def to_internal(self) -> NetworkFlowTopTableDashletConfig:
        return NetworkFlowTopTableDashletConfig(
            type=self.internal_type(),
            dimension=self.dimension,
            accent=self.accent,
            limit_to=self.limit_to,
        )


@api_model
class NetworkFlowDonutContent(BaseWidgetContent):
    type: Literal["network_flow_donut"] = api_field(
        description="Displays a network flow breakdown as a donut chart with share-of-total slices."
    )
    dimension: NetworkFlowDonutDimension = api_field(
        description="Which dimension to break the traffic down by (applications or protocols)."
    )
    limit_to: int = api_field(
        description="Maximum number of slices to display before the rest are grouped as 'Other'."
    )
    legend_mode: NetworkFlowDonutLegendMode = api_field(
        description="Whether the legend states the volume per category in a table, or names the "
        "categories as compact chips below the chart."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "network_flow_donut"

    @classmethod
    def from_internal(cls, config: NetworkFlowDonutDashletConfig) -> Self:
        return cls(
            type="network_flow_donut",
            dimension=config["dimension"],
            limit_to=config["limit_to"],
            # Widgets stored before the legend became configurable listed the shares.
            legend_mode=config.get("legend_mode", "table"),
        )

    @override
    def to_internal(self) -> NetworkFlowDonutDashletConfig:
        return NetworkFlowDonutDashletConfig(
            type=self.internal_type(),
            dimension=self.dimension,
            limit_to=self.limit_to,
            legend_mode=self.legend_mode,
        )


@api_model
class NetworkFlowKpiStatCardContent(BaseWidgetContent):
    type: Literal["network_flow_kpi_stat_card"] = api_field(
        description="Displays a single headline network flow metric with an optional change "
        "indicator and a trend sparkline."
    )
    metric: NetworkFlowKpiStatCardMetric = api_field(
        description="Which metric to display (byte volumes or activity counts). The unit "
        "formatting follows the metric."
    )
    accent: NetworkFlowAccent = api_field(description="Accent color of the sparkline.")
    show_delta: bool = api_field(
        description="Whether to show the change versus the previous period."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "network_flow_kpi_stat_card"

    @classmethod
    def from_internal(cls, config: NetworkFlowKpiStatCardDashletConfig) -> Self:
        return cls(
            type="network_flow_kpi_stat_card",
            metric=config["metric"],
            accent=config["accent"],
            show_delta=config["show_delta"],
        )

    @override
    def to_internal(self) -> NetworkFlowKpiStatCardDashletConfig:
        return NetworkFlowKpiStatCardDashletConfig(
            type=self.internal_type(),
            metric=self.metric,
            accent=self.accent,
            show_delta=self.show_delta,
        )


@api_model
class NetworkFlowTrendChartContent(BaseWidgetContent):
    type: Literal["network_flow_trend_chart"] = api_field(
        description="Displays how network flow traffic evolved over time, broken down into "
        "the top series of a dimension."
    )
    dimension: NetworkFlowTrendChartDimension = api_field(
        description="Which dimension to break the traffic down into series (applications, "
        "autonomous systems, or the total bandwidth split into ingress and egress)."
    )
    display_mode: NetworkFlowTrendChartDisplayMode = api_field(
        description="Whether to draw the series as separate lines or as cumulative stacked areas."
    )
    limit_to: int = api_field(
        description="Maximum number of top series to plot before the rest are dropped."
    )
    show_legend: bool = api_field(description="Whether to list the plotted series below the graph.")

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "network_flow_trend_chart"

    @classmethod
    def from_internal(cls, config: NetworkFlowTrendChartDashletConfig) -> Self:
        return cls(
            type="network_flow_trend_chart",
            dimension=config["dimension"],
            display_mode=config["display_mode"],
            limit_to=config["limit_to"],
            # Widgets stored before the legend became optional always showed it.
            show_legend=config.get("show_legend", True),
        )

    @override
    def to_internal(self) -> NetworkFlowTrendChartDashletConfig:
        return NetworkFlowTrendChartDashletConfig(
            type=self.internal_type(),
            dimension=self.dimension,
            display_mode=self.display_mode,
            limit_to=self.limit_to,
            show_legend=self.show_legend,
        )
