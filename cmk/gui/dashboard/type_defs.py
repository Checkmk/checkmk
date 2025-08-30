#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, NewType, NotRequired, TypedDict

from cmk.gui.type_defs import (
    FilterName,
    GraphPresentation,
    GraphRenderOptionsVS,
    SingleInfos,
    Visual,
    VisualContext,
)
from cmk.gui.valuespec import HostStateValue, MonitoringStateValue, TimerangeValue

DashboardName = str
DashletId = int
DashletRefreshInterval = bool | int
DashletRefreshAction = str | None
DashletSize = tuple[int, int]
DashletPosition = tuple[int, int]
ResponsiveGridLayoutID = NewType("ResponsiveGridLayoutID", str)

# NOTE: this is limited to 5 different breakpoints, as the library only officially supports 5 types
#       see the frontend implementation for more details
type ResponsiveGridBreakpoint = Literal["XS", "S", "M", "L", "XL"]


class DashletSizeAndPosition(TypedDict):
    size: DashletSize
    position: DashletPosition


class _DashletConfigMandatory(TypedDict):
    type: str


class DashletConfig(_DashletConfigMandatory, total=False):
    single_infos: SingleInfos
    title: str
    title_url: str
    context: VisualContext
    # TODO: Could not a place which sets this flag. Can we remove it?
    reload_on_resize: bool
    position: DashletPosition
    size: DashletSize
    responsive_grid_layouts: dict[
        ResponsiveGridLayoutID, dict[ResponsiveGridBreakpoint, DashletSizeAndPosition]
    ]
    background: bool
    show_title: bool | Literal["transparent"]


class ABCGraphDashletConfig(DashletConfig):
    timerange: TimerangeValue
    graph_render_options: GraphRenderOptionsVS


class ProblemsGraphDashletConfig(ABCGraphDashletConfig): ...


class CombinedGraphDashletConfig(ABCGraphDashletConfig):
    graph_template: str
    presentation: GraphPresentation


class SingleTimeseriesDashletConfig(ABCGraphDashletConfig):
    metric: str
    color: str


class CustomGraphDashletConfig(ABCGraphDashletConfig):
    custom_graph: str
    # Seems to be some old option which is still referenced by some migration code.
    # See CustomGraphDashlet._migrate_show_legend_to_graph_render_options for additional information
    # TODO: Investigate whether there is/was migration code in place and if this can be removed
    show_legend: NotRequired[bool]


class MetricTimeRangeParameters(TypedDict):
    window: TimerangeValue
    rrd_consolidation: Literal["average", "min", "max"]


type MetricTimeRange = Literal["current"] | tuple[Literal["range"], MetricTimeRangeParameters]
type MetricDisplayRangeFixed = tuple[Literal["fixed"], Any]
type MetricDisplayRangeWithAutomatic = MetricDisplayRangeFixed | Literal["automatic"]
type StatusDisplay = None | tuple[Literal["background"], Literal["all", "not_ok"]]
type StatusDisplayWithText = StatusDisplay | tuple[Literal["text"], Literal["all", "not_ok"]]


class SingleMetricDashletConfig(DashletConfig):
    metric: str


class BarplotDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeWithAutomatic


class GaugeDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeFixed
    time_range: MetricTimeRange
    status_display: StatusDisplayWithText


class SingleGraphDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeWithAutomatic  # TODO: remove once the old setup page is gone
    toggle_range_display: bool  # TODO: remove once the old setup page is gone
    time_range: MetricTimeRange
    status_display: StatusDisplayWithText


class AverageScatterplotDashletConfig(DashletConfig):
    metric: str
    time_range: TimerangeValue
    metric_color: str | None
    avg_color: str | None
    median_color: str | None


class TopListColumnConfig(TypedDict):
    show_service_description: NotRequired[Literal[True]]
    show_bar_visualization: NotRequired[Literal[True]]


class TopListDashletConfig(DashletConfig):
    metric: str
    columns: TopListColumnConfig
    display_range: MetricDisplayRangeWithAutomatic
    ranking_order: Literal["high", "low"]
    limit_to: int


class StateDashletConfig(DashletConfig):
    status_display: StatusDisplay
    show_summary: Literal["not_ok"] | None


class HostStateSummaryDashletConfig(DashletConfig):
    state: HostStateValue


class ServiceStateSummaryDashletConfig(DashletConfig):
    state: MonitoringStateValue


class InventoryDashletConfig(DashletConfig):
    inventory_path: str


class AlertOverviewDashletConfig(DashletConfig):
    time_range: TimerangeValue
    limit_objects: NotRequired[int]


class SiteOverviewDashletConfig(DashletConfig):
    dataset: NotRequired[Literal["hosts", "sites"]]
    box_scale: NotRequired[Literal["default", "large"]]


class EventBarChartRenderBarChart(TypedDict):
    time_range: TimerangeValue
    time_resolution: Literal["h", "d"]


class EventBarChartRenderSimpleNumber(TypedDict):
    time_range: TimerangeValue


type EventBarChartRenderMode = (
    tuple[Literal["bar_chart"], EventBarChartRenderBarChart]
    | tuple[Literal["simple_number"], EventBarChartRenderSimpleNumber]
)


class EventBarChartDashletConfig(DashletConfig):
    render_mode: EventBarChartRenderMode
    log_target: Literal["both", "host", "service"]


class NtopAlertsDashletConfig(DashletConfig): ...


class NtopFlowsDashletConfig(DashletConfig): ...


class NtopTopTalkersDashletConfig(DashletConfig): ...


class DashboardRelativeGridLayoutSpec(TypedDict):
    type: Literal["relative_grid"]


class DashboardResponsiveGridLayoutSettings(TypedDict):
    title: str
    breakpoints: set[ResponsiveGridBreakpoint]


class DashboardResponsiveGridLayoutSpec(TypedDict):
    type: Literal["responsive_grid"]
    layouts: dict[ResponsiveGridLayoutID, DashboardResponsiveGridLayoutSettings]


class DashboardConfig(Visual):
    # TODO: rename dashlets to widgets, change list to dict -> update action
    #       this can include complete overhaul for how widgets are stored
    mtime: int
    dashlets: list[DashletConfig]
    show_title: bool
    mandatory_context_filters: list[FilterName]
    layout: NotRequired[
        DashboardRelativeGridLayoutSpec | DashboardResponsiveGridLayoutSpec
    ]  # default: relative_grid
