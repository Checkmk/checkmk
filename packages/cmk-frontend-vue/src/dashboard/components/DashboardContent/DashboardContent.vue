<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Component } from 'vue'

import DashboardContentEmbeddedView from './DashboardContentEmbeddedView.vue'
import DashboardContentFigure from './DashboardContentFigure.vue'
import DashboardContentGraph from './DashboardContentGraph.vue'
import DashboardContentIFrame from './DashboardContentIFrame.vue'
import DashboardContentLinkedView from './DashboardContentLinkedView.vue'
import DashboardContentNtop from './DashboardContentNtop.vue'
import DashboardContentSidebarElement from './DashboardContentSidebarElement.vue'
import DashboardContentSingleMetric from './DashboardContentSingleMetric.vue'
import DashboardContentStaticText from './DashboardContentStaticText.vue'
import DashboardContentTimeSeriesGraph from './DashboardContentTimeSeriesGraph.vue'
import DashboardContentTimelineCount from './DashboardContentTimelineCount.vue'
import DashboardContentTopList from './DashboardContentTopList.vue'
import DashboardContentUserMessages from './DashboardContentUserMessages.vue'
import DashboardContentNetworkFlowDonut from './NetworkFlow/DashboardContentNetworkFlowDonut.vue'
import DashboardContentNetworkFlowKpiStatCard from './NetworkFlow/DashboardContentNetworkFlowKpiStatCard.vue'
import DashboardContentNetworkFlowTopTable from './NetworkFlow/DashboardContentNetworkFlowTopTable.vue'
import DashboardContentNetworkFlowTrendChart from './NetworkFlow/DashboardContentNetworkFlowTrendChart.vue'
import { CONTENT_FIGURE_TYPES, GRAPH_TYPES, NTOP_TYPES } from './types.ts'
</script>

<script setup lang="ts">
import type { TimelineContent, WidgetContent } from '@/dashboard/types/widget'

import type { ContentProps } from './types.ts'

defineProps<ContentProps>()

function isTimeline(content: WidgetContent): content is TimelineContent {
  return content.type === 'alert_timeline' || content.type === 'notification_timeline'
}

// Dispatch is by content type, except for the timelines: their render mode decides
// whether they are a chart over time or a single number, and the two are drawn by
// different components.
function contentToComponent(content: WidgetContent): Component {
  const contentType: string = content.type
  switch (true) {
    // NOTE: this branch must match with the keys generated in componentKey() below.
    case isTimeline(content) && content.render_mode.type === 'simple_number':
      return DashboardContentTimelineCount
    case contentType === 'url':
      return DashboardContentIFrame
    case contentType === 'linked_view':
      return DashboardContentLinkedView
    case contentType === 'embedded_view':
      return DashboardContentEmbeddedView
    case contentType === 'static_text':
      return DashboardContentStaticText
    case contentType === 'top_list':
      return DashboardContentTopList
    case contentType === 'single_metric':
      return DashboardContentSingleMetric
    case contentType === 'network_flow_top_table':
      return DashboardContentNetworkFlowTopTable
    case contentType === 'network_flow_donut':
      return DashboardContentNetworkFlowDonut
    case contentType === 'network_flow_kpi_stat_card':
      return DashboardContentNetworkFlowKpiStatCard
    case contentType === 'network_flow_trend_chart':
      return DashboardContentNetworkFlowTrendChart
    case contentType === 'user_messages':
      return DashboardContentUserMessages
    case contentType === 'sidebar_element':
      return DashboardContentSidebarElement
    // These graph widgets render client-side on the new graphing engine. The remaining
    // GRAPH_TYPES still fall through to their legacy components below.
    case [
      'performance_graph',
      'single_timeseries',
      'combined_graph',
      'average_scatterplot',
      'problem_graph',
      'custom_graph'
    ].includes(contentType):
      return DashboardContentTimeSeriesGraph
    case CONTENT_FIGURE_TYPES.includes(contentType):
      return DashboardContentFigure
    case GRAPH_TYPES.includes(contentType):
      return DashboardContentGraph
    case NTOP_TYPES.includes(contentType):
      return DashboardContentNtop
    default:
      throw new Error(`Unknown dashboard content type: ${contentType}`)
  }
}

function componentKey(content: WidgetContent): string {
  if (isTimeline(content)) {
    return `${content.type}-${content.render_mode.type}`
  }
  return content.type
}
</script>

<template>
  <component
    :is="contentToComponent(content)"
    :key="componentKey(content)"
    :widget_id="widget_id"
    :general_settings="general_settings"
    :content="content"
    :effective-title="effectiveTitle"
    :effective_filter_context="effective_filter_context"
    :dashboard-key="dashboardKey"
    :is-preview="isPreview"
  />
</template>
