<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Component } from 'vue'

import DashboardContentEmbeddedView from './DashboardContentEmbeddedView.vue'
import DashboardContentIFrame from './DashboardContentIFrame.vue'
import DashboardContentLinkedView from './DashboardContentLinkedView.vue'
import DashboardContentMonitoringTable from './DashboardContentMonitoringTable.vue'
import DashboardContentNtop from './DashboardContentNtop.vue'
import DashboardContentSidebarElement from './DashboardContentSidebarElement.vue'
import DashboardContentStaticText from './DashboardContentStaticText.vue'
import DashboardContentTimeSeriesGraph from './DashboardContentTimeSeriesGraph.vue'
import DashboardContentTimeline from './DashboardContentTimeline.vue'
import DashboardContentUserMessages from './DashboardContentUserMessages.vue'
import DashboardContentAlertOverview from './figures/DashboardContentAlertOverview.vue'
import DashboardContentBarplot from './figures/DashboardContentBarplot.vue'
import DashboardContentGauge from './figures/DashboardContentGauge.vue'
import DashboardContentInventory from './figures/DashboardContentInventory.vue'
import DashboardContentSingleMetric from './figures/DashboardContentSingleMetric.vue'
import DashboardContentSiteOverview from './figures/DashboardContentSiteOverview.vue'
import DashboardContentState from './figures/DashboardContentState.vue'
import DashboardContentStateSummary from './figures/DashboardContentStateSummary.vue'
import DashboardContentStats from './figures/DashboardContentStats.vue'
import DashboardContentTimelineCount from './figures/DashboardContentTimelineCount.vue'
import DashboardContentTopList from './figures/DashboardContentTopList.vue'
import { NTOP_TYPES } from './types.ts'
</script>

<script setup lang="ts">
import type { TimelineContent, WidgetContent, WidgetEmitTimeRange } from '@/dashboard/types/widget'

import type { ContentProps } from './types.ts'

defineProps<ContentProps>()
defineEmits<WidgetEmitTimeRange>()

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
    case isTimeline(content):
      return DashboardContentTimeline
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
    case contentType === 'user_messages':
      return DashboardContentUserMessages
    case contentType === 'sidebar_element':
      return DashboardContentSidebarElement
    // Every graph widget renders client-side on the new graphing engine.
    case [
      'performance_graph',
      'single_timeseries',
      'combined_graph',
      'average_scatterplot',
      'problem_graph',
      'custom_graph',
      'embedded_custom_graph'
    ].includes(contentType):
      return DashboardContentTimeSeriesGraph
    case ['host_stats', 'service_stats', 'event_stats'].includes(contentType):
      return DashboardContentStats
    case contentType === 'barplot':
      return DashboardContentBarplot
    case contentType === 'gauge':
      return DashboardContentGauge
    case ['host_state', 'service_state'].includes(contentType):
      return DashboardContentState
    case ['host_state_summary', 'service_state_summary'].includes(contentType):
      return DashboardContentStateSummary
    case contentType === 'inventory':
      return DashboardContentInventory
    case contentType === 'site_overview':
      return DashboardContentSiteOverview
    case contentType === 'alert_overview':
      return DashboardContentAlertOverview
    case contentType === 'monitoring_table':
      return DashboardContentMonitoringTable
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
    :tick="tick"
    :range="range"
    @update-time-range="$emit('updateTimeRange', $event)"
  />
</template>
