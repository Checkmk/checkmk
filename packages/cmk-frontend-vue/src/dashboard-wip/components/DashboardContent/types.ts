/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  EffectiveWidgetFilterContext,
  WidgetContent,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget.ts'

// General
export interface ContentProps {
  widget_id: string
  general_settings: WidgetGeneralSettings
  content: WidgetContent
  effective_filter_context: EffectiveWidgetFilterContext
  dashboardName: string
}
export type ContentPropsRecord = Readonly<Record<string, ContentProps>>

// Figure
export const CONTENT_FIGURE_TYPES: string[] = [
  'alert_overview',
  'alert_timeline',
  'average_scatterplot',
  'barplot',
  'event_stats',
  'gauge',
  'host_state',
  'host_state_summary',
  'host_stats',
  'inventory',
  'notification_timeline',
  'service_state',
  'service_state_summary',
  'service_stats',
  'single_metric',
  'site_overview'
]

export type ContentFigureType = (typeof CONTENT_FIGURE_TYPES)[number]

// Graph
export const GRAPH_TYPES = [
  'combined_graph',
  'custom_graph',
  'performance_graph',
  'problem_graph',
  'single_timeseries'
]

// Ntop
export const NTOP_TYPES: string[] = ['ntop_alerts', 'ntop_flows', 'ntop_top_talkers']

export type NtopType = (typeof NTOP_TYPES)[number]
