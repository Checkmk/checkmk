/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

import type { WidgetItemList } from '@/dashboard/components/Wizard/components/WidgetSelection/types'

const { _t } = usei18n()

export enum VisualizationTimelineType {
  BARPLOT = 'bar_chart',
  METRIC = 'simple_number'
}

export const getVisualizationTypes = (): WidgetItemList => {
  return [
    { id: VisualizationTimelineType.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
    { id: VisualizationTimelineType.METRIC, label: _t('Metric'), icon: 'single-metric' }
  ]
}

export enum Graph {
  ALERT_OVERVIEW = 'alert_overview',
  ALERT_TIMELINE = 'alert_timeline',
  NOTIFICATION_TIMELINE = 'notification_timeline',
  PROBLEM_GRAPH = 'problem_graph'
}

export const getAvailableGraphs = (): Graph[] => {
  return [
    Graph.ALERT_OVERVIEW,
    Graph.ALERT_TIMELINE,
    Graph.NOTIFICATION_TIMELINE,
    Graph.PROBLEM_GRAPH
  ]
}

export const getAvailableWidgets = (): WidgetItemList => {
  return [
    { id: Graph.ALERT_OVERVIEW, label: _t('Alert overview'), icon: 'alert-overview' },
    { id: Graph.ALERT_TIMELINE, label: _t('Alert timeline'), icon: 'alert-timeline' },
    {
      id: Graph.NOTIFICATION_TIMELINE,
      label: _t('Notification timeline'),
      icon: 'notification-timeline'
    },
    {
      id: Graph.PROBLEM_GRAPH,
      label: _t('Percentage of service problems'),
      icon: 'percentage-of-service-problems'
    }
  ]
}

export const getLogCompatibleGraphs = (): Graph[] => {
  return [Graph.ALERT_TIMELINE, Graph.NOTIFICATION_TIMELINE]
}

export const getGraphFromWidgetType = (widgetType: string): Graph => {
  switch (widgetType) {
    case 'alert_timeline':
      return Graph.ALERT_TIMELINE

    case 'notification_timeline':
      return Graph.NOTIFICATION_TIMELINE

    case 'problem_graph':
      return Graph.PROBLEM_GRAPH

    case 'alert_overview':
    default: {
      return Graph.ALERT_OVERVIEW
    }
  }
}
