/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

export type ComputedWidgetSpecResponse =
  components['schemas']['ComputedWidgetResponse_ComputedWidgetSpec_']
export type ComputedTopList = components['schemas']['TopList']
export type TopListEntry = components['schemas']['TopListEntry']
export type TopListError = components['schemas']['TopListError']
export type ComputedSingleMetric = components['schemas']['SingleMetric']

export type WidgetContent = components['schemas']['WidgetContent']
export type WidgetSizeValue = components['schemas']['WidgetSizeValue']
export type WidgetGeneralSettings = components['schemas']['WidgetGeneralSettings']
export type WidgetFilterContext = components['schemas']['WidgetFilterContext']

export type RelativeGridWidget = components['schemas']['RelativeGridWidgetResponse']
export type ResponsiveGridWidget = components['schemas']['ResponsiveGridWidgetResponse']

export type AnyWidget = RelativeGridWidget | ResponsiveGridWidget

export type RelativeGridWidgets = components['schemas']['RelativeGridDashboardResponse']['widgets']
export type ResponsiveGridWidgets =
  components['schemas']['ResponsiveGridDashboardResponse']['widgets']

export type RelativeGridWidgetLayout = components['schemas']['WidgetRelativeGridLayout']
export type ResponsiveGridWidgetLayouts = components['schemas']['WidgetResponsiveGridLayouts']

export type WidgetLayout = RelativeGridWidgetLayout | ResponsiveGridWidgetLayouts
export interface WidgetSpec {
  content: WidgetContent
  filter_context: WidgetFilterContext
  general_settings: WidgetGeneralSettings
}
export type WidgetContentType = components['schemas']['WidgetContent']['type']

export type ResponsiveGridWidgetLayout = components['schemas']['WidgetResponsiveGridLayout']

export type AnnotatedInfoName = components['schemas']['AnnotatedInfoName']

export interface EffectiveWidgetFilterContext extends WidgetFilterContext {
  restricted_to_single: AnnotatedInfoName[]
}

export type FilterHTTPVars = Record<string, string>
export type VisualContext = Record<string, FilterHTTPVars>

export interface ComputedWidgetResponse<T> {
  domainType: 'widget-compute'
  value: T
}

export type SavedWidgetContent = components['schemas']['SavedWidgetContent']
export type WidgetTimeRange = components['schemas']['WidgetTimeRange']
export type ResolvedLink = components['schemas']['ResolvedLink']
export type LinkProperties = components['schemas']['LinkProperties']
export type FilterResult = components['schemas']['FilterResult']
export interface ExplicitWidgetContent<C> {
  type: 'explicit'
  content: C
  context: VisualContext
}
export type WidgetSource<C> = ExplicitWidgetContent<C> | SavedWidgetContent

// Specific widget types
export type EmbeddedViewContent = components['schemas']['EmbeddedViewContent']
export type IFrameContent = components['schemas']['URLContent']
export type LinkedViewContent = components['schemas']['LinkedViewContent']
export type StaticTextContent = components['schemas']['StaticTextContent']
export type TopListContent = components['schemas']['TopListContent']
export type NetworkFlowTopTableContent = components['schemas']['NetworkFlowTopTableContent']
export type ComputedNetworkFlowTopTable = components['schemas']['ComputedNetworkFlowTopTable']
export type NetworkFlowDonutContent = components['schemas']['NetworkFlowDonutContent']
export type ComputedNetworkFlowDonutSlice = components['schemas']['ComputedNetworkFlowDonutSlice']
export type ComputedNetworkFlowDonut = components['schemas']['ComputedNetworkFlowDonut']
export type NetworkFlowKpiStatCardContent = components['schemas']['NetworkFlowKpiStatCardContent']
export type ComputedNetworkFlowKpiStatCard = components['schemas']['ComputedNetworkFlowKpiStatCard']
export type NetworkFlowTrendChartContent = components['schemas']['NetworkFlowTrendChartContent']
export type ComputedNetworkFlowTrendChart = components['schemas']['ComputedNetworkFlowTrendChart']
export type SidebarElementContent = components['schemas']['SidebarElementContent']
export type PerformanceGraphContent = components['schemas']['PerformanceGraphContent']
export type SingleTimeseriesContent = components['schemas']['SingleTimeseriesContent']
export type SingleMetricContent = components['schemas']['SingleMetricContent']
export type StatsContent = components['schemas']['StatsContent']
export type Stats = components['schemas']['Stats']
export type BarplotContent = components['schemas']['BarplotContent']
export type Barplot = components['schemas']['Barplot']
export type BarplotBar = components['schemas']['BarplotBar']
export type GaugeContent = components['schemas']['GaugeContent']
export type Gauge = components['schemas']['Gauge']
export type GaugeStatus = components['schemas']['GaugeStatus']
export type InventoryContent = components['schemas']['InventoryContent']
export type InventoryAttribute = components['schemas']['InventoryAttribute']
export type AlertOverviewContent = components['schemas']['AlertOverviewContent']
export type AlertOverview = components['schemas']['AlertOverview']
export type TimelineCount = components['schemas']['TimelineCount']
export type AlertOverviewElement = components['schemas']['AlertOverviewElement']
export type SiteOverviewContent = components['schemas']['SiteOverviewContent']
export type MonitoringTableContent = components['schemas']['MonitoringTableContent']
export type ComputedMonitoringTable = components['schemas']['MonitoringTable']
export type SiteOverview = components['schemas']['SiteOverview']
export type SiteOverviewHost = components['schemas']['SiteOverviewHost']
export type SiteOverviewHosts = components['schemas']['SiteOverviewHosts']
export type MonitoringState = components['schemas']['MonitoringState']
export type HostState = components['schemas']['HostState']
export type SiteOverviewSites = components['schemas']['SiteOverviewSites']
export type StateContent = components['schemas']['StateContent']
export type HostOrServiceState = components['schemas']['HostOrServiceState']
export type StateSummaryContent = components['schemas']['StateSummaryContent']
export type StateSummary = components['schemas']['StateSummary']
export type StatsPart = components['schemas']['StatsPart']
export type AlertTimelineContent = components['schemas']['AlertTimelineContent']
export type NotificationTimelineContent = components['schemas']['NotificationTimelineContent']
/** Either timeline widget; they share their render modes and their computed count. */
export type TimelineContent = AlertTimelineContent | NotificationTimelineContent
export type CombinedGraphContent = components['schemas']['CombinedGraphContent']
export type AverageScatterplotContent = components['schemas']['AverageScatterplotContent']
export type ProblemGraphContent = components['schemas']['ProblemGraphContent']
export type CustomGraphContent = components['schemas']['CustomGraphContent']
export type EmbeddedCustomGraphContent = components['schemas']['EmbeddedCustomGraphContent']
// Only picks graph_render_options, used to check legend visibility in the scrollable preview
// as this is used by multiple widget types we extract it only once here
export type GraphWidgetContent = Pick<
  components['schemas']['PerformanceGraphContent'],
  'graph_render_options'
>
export type WidgetAvailableInventory =
  components['schemas']['WidgetAvailableInventoryCollectionModel']

export interface WidgetInteractionState {
  editMode: boolean
  isPreview: boolean
}

export interface WidgetEmitTimeRange {
  updateTimeRange: [range: DateTimeRange]
}
