/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

import type { WidgetItemList } from '@/dashboard-wip/components/Wizard/components/WidgetSelection/types'

const { _t } = usei18n()

export enum VisualizationTimelineType {
  BARPLOT = 'BARPLOT',
  METRIC = 'METRIC'
}

export const getVisualizationTypes = (): WidgetItemList => {
  return [
    { id: VisualizationTimelineType.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
    { id: VisualizationTimelineType.METRIC, label: _t('Metric'), icon: 'single-metric' }
  ]
}

export enum Graph {
  ALERT_OVERVIEW = 'ALERT_OVERVIEW',
  ALERT_TIMELINE = 'ALERT_TIMELINE',
  NOTIFICATION_TIMELINE = 'NOTIFICATION_TIMELINE',
  PERCENTAGE_OF_SERVICE_PROBLEMS = 'PERCENTAGE_OF_SERVICE_PROBLEMS'
}

export const getAvailableGraphs = (): Graph[] => {
  return [
    Graph.ALERT_OVERVIEW,
    Graph.ALERT_TIMELINE,
    Graph.NOTIFICATION_TIMELINE,
    Graph.PERCENTAGE_OF_SERVICE_PROBLEMS
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
      id: Graph.PERCENTAGE_OF_SERVICE_PROBLEMS,
      label: _t('Percentage of service problems'),
      icon: 'percentage-of-service-problems'
    }
  ]
}
