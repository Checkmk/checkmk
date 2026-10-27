#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NewType, NotRequired, TypedDict

from cmk.gui.type_defs import (
    ColumnSpec,
    ContextualLinkEntryConfig,
    ContextualLinkLocationConfig,
    DashboardEmbeddedViewSpec,
    FilterName,
    GraphLegendStyle,
    GraphPresentation,
    GraphRenderOptionsVS,
    InventoryJoinMacrosSpec,
    SingleInfos,
    SorterSpec,
    Visual,
    VisualContext,
)
from cmk.gui.type_defs import ContextFilterConfig as ContextFilterConfig
from cmk.gui.type_defs import ContextualLinkTargetType as ContextualLinkTargetType
from cmk.gui.valuespec import HostStateValue, MonitoringStateValue, TimerangeValue

DashboardName = str
WidgetId = str
DashletRefreshInterval = bool | int
DashletRefreshAction = str | None
DashletSize = tuple[int, int]
DashletPosition = tuple[int, int]
ResponsiveGridLayoutID = NewType("ResponsiveGridLayoutID", str)
DEFAULT_RESPONSIVE_GRID_LAYOUT_ID = ResponsiveGridLayoutID("default")

# NOTE: this is limited to 5 different breakpoints, as the library only officially supports 5 types
#       see the frontend implementation for more details
type ResponsiveGridBreakpoint = Literal["XS", "S", "M", "L", "XL"]


class DashletSizeAndPosition(TypedDict):
    size: DashletSize
    position: DashletPosition


class ContextualLinkNoneConfig(TypedDict):
    type: Literal["none"]


class ContextualLinkInheritedConfig(TypedDict):
    type: Literal["inherited"]
    location: ContextualLinkLocationConfig
    include_context: bool
    include_time_range: bool
    show_filter_form: bool


class ContextualLinkCustomConfig(TypedDict):
    type: Literal["custom"]
    links: list[ContextualLinkEntryConfig]


# A widget in `default` mode stores no link key, so `default` has no persisted form.
type ContextualLinkConfig = (
    ContextualLinkNoneConfig | ContextualLinkInheritedConfig | ContextualLinkCustomConfig
)


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
    background: NotRequired[bool]
    show_title: bool | Literal["transparent"]


class FixedWindow(TypedDict):
    type: Literal["range"]
    window: TimerangeValue


class DashboardWindow(TypedDict):
    type: Literal["dashboard"]


class ABCGraphDashletConfig(DashletConfig):
    timerange: DashboardWindow | FixedWindow
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


class EmbeddedCustomGraphDashletConfig(ABCGraphDashletConfig):
    # Stored config of the embedded_custom_graph widget. `definition` is the dumped
    # CustomGraphContentV2 (nonfree/pro), including "version"; community code only passes it
    # through, the registered pro widget parses and validates it.
    definition: dict[str, object]


class MetricCurrentValue(TypedDict):
    type: Literal["current"]


class MetricFixedWindow(FixedWindow):
    rrd_consolidation: Literal["average", "min", "max"]


class MetricDashboardWindow(DashboardWindow):
    rrd_consolidation: Literal["average", "min", "max"]


type MetricTimeRange = MetricCurrentValue | MetricFixedWindow | MetricDashboardWindow
type MetricDisplayRangeFixed = tuple[Literal["fixed"], tuple[str, tuple[float, float]]]
type MetricDisplayRangeWithAutomatic = MetricDisplayRangeFixed | Literal["automatic"]
type StatusDisplay = None | tuple[Literal["background"], Literal["all", "not_ok"]]
type StatusDisplayWithText = StatusDisplay | tuple[Literal["text"], Literal["all", "not_ok"]]


class SingleMetricDashletConfig(DashletConfig):
    metric: str


class BarplotDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeWithAutomatic
    contextual_link: NotRequired[ContextualLinkConfig]


class GaugeDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeFixed
    time_range: MetricTimeRange
    status_display: StatusDisplayWithText


SingleMetricSparkHeightMode = Literal["band", "full"]


class SingleGraphDashletConfig(SingleMetricDashletConfig):
    display_range: MetricDisplayRangeWithAutomatic  # TODO: remove once the old setup page is gone
    toggle_range_display: bool  # TODO: remove once the old setup page is gone
    time_range: MetricTimeRange
    status_display: StatusDisplayWithText
    spark_height_mode: NotRequired[SingleMetricSparkHeightMode]
    show_delta: NotRequired[bool]


class AverageScatterplotDashletConfig(DashletConfig):
    metric: str
    time_range: DashboardWindow | FixedWindow
    metric_color: str | None
    avg_color: str | None
    median_color: str | None
    show_legend: NotRequired[bool]
    legend_style: NotRequired[GraphLegendStyle]


class TopListColumnConfig(TypedDict):
    show_service_description: NotRequired[Literal[True]]
    show_bar_visualization: NotRequired[Literal[True]]


class TopListDashletConfig(DashletConfig):
    metric: str
    columns: TopListColumnConfig
    display_range: MetricDisplayRangeWithAutomatic
    ranking_order: Literal["high", "low"]
    limit_to: int
    contextual_link: NotRequired[ContextualLinkConfig]


class StatsDashletConfig(DashletConfig):
    contextual_link: NotRequired[ContextualLinkConfig]


class StateDashletConfig(DashletConfig):
    status_display: StatusDisplay
    show_summary: Literal["not_ok"] | None
    contextual_link: NotRequired[ContextualLinkConfig]


class HostStateSummaryDashletConfig(DashletConfig):
    state: HostStateValue


class ServiceStateSummaryDashletConfig(DashletConfig):
    state: MonitoringStateValue


class InventoryDashletConfig(DashletConfig):
    inventory_path: str
    contextual_link: NotRequired[ContextualLinkConfig]


class AlertOverviewDashletConfig(DashletConfig):
    time_range: DashboardWindow | FixedWindow
    limit_objects: NotRequired[int]


type MonitoringTableName = Literal["hosts", "services"]

# The display options of the monitoring pages for their timestamp columns.
type MonitoringTableDateFormat = Literal["%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d.%m.", "%m/%d"]
type MonitoringTableTimestampFormat = Literal["mixed", "abs", "rel", "both", "epoch"]


class MonitoringTableDashletConfig(DashletConfig):
    table: MonitoringTableName
    columns: Sequence[str]
    sort: Sequence[str]
    limit: int
    date_format: NotRequired[MonitoringTableDateFormat]
    timestamp_format: NotRequired[MonitoringTableTimestampFormat]


class SiteOverviewDashletConfig(DashletConfig):
    dataset: NotRequired[Literal["hosts", "sites"]]
    box_scale: NotRequired[Literal["default", "large"]]
    contextual_link: NotRequired[ContextualLinkConfig]


class EventBarChartRenderBarChart(TypedDict):
    time_range: DashboardWindow | FixedWindow
    time_resolution: Literal["h", "d"]


class EventBarChartRenderSimpleNumber(TypedDict):
    time_range: DashboardWindow | FixedWindow


type EventBarChartRenderMode = (
    tuple[Literal["bar_chart"], EventBarChartRenderBarChart]
    | tuple[Literal["simple_number"], EventBarChartRenderSimpleNumber]
)


class EventBarChartDashletConfig(DashletConfig):
    render_mode: EventBarChartRenderMode
    log_target: Literal["both", "host", "service"]


class ABCViewDashletConfig(DashletConfig):
    name: str


class LinkedViewDashletConfig(ABCViewDashletConfig): ...


class EmbeddedViewDashletConfig(ABCViewDashletConfig):
    datasource: str


class ViewDashletConfig(ABCViewDashletConfig):
    # These fields are redundant between DashletConfig and Visual
    # name: str
    # context: VisualContext
    # single_infos: SingleInfos
    # title: str | LazyString
    add_context_to_title: bool
    sort_index: int
    is_show_more: bool
    # From: ViewSpec
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: list[ColumnSpec]
    painters: list[ColumnSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup"]
    sorters: Sequence[SorterSpec]
    add_headers: NotRequired[str]
    # View editor only adds them in case they are truish. In our built-in specs these flags are also
    # partially set in case they are falsy
    mobile: NotRequired[bool]
    mustsearch: NotRequired[bool]
    force_checkboxes: NotRequired[bool]
    play_sounds: NotRequired[bool]
    user_sortable: NotRequired[bool]
    inventory_join_macros: NotRequired[InventoryJoinMacrosSpec]
    modified_at: NotRequired[str]  # timestamp in ISO format


class SnapinDashletConfig(DashletConfig):
    snapin: str


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
    mtime: int
    widgets: dict[WidgetId, DashletConfig]
    show_title: bool
    mandatory_context_filters: list[FilterName]
    layout: NotRequired[
        DashboardRelativeGridLayoutSpec | DashboardResponsiveGridLayoutSpec
    ]  # default: relative_grid
    # embedded_views only present for 2.5+ dashboard config format
    # view definitions for embedded view widgets
    embedded_views: dict[str, DashboardEmbeddedViewSpec]
    public_token_id: NotRequired[str | None]
