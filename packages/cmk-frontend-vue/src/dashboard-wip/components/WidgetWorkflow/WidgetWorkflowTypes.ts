/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

const { _t } = usei18n()

export interface WorkflowItem {
  title: TranslatedString
  subtitle: TranslatedString

  icon: SimpleIcons
  icon_emblem?: SimpleIcons | undefined
}

export const dashboardWidgetWorkflows: Record<string, WorkflowItem> = {
  metrics_graphs: {
    title: _t('Metrics & graphs'),
    subtitle: _t('Visualize key metrics using charts and graphs'),
    icon: 'graph'
  },
  custom_graphs: {
    title: _t('Custom graphs'),
    subtitle: _t('Visualize built-in and preconfigured custom graphs'),
    icon: 'graph',
    icon_emblem: 'add'
  },
  views: {
    title: _t('Views'),
    subtitle: _t('Embed saved views'),
    icon: 'view'
  },
  host_site_overview: {
    title: _t('Host & site overview'),
    subtitle: _t('Summarize key system components'),
    icon: 'site-overview'
  },
  service_overview: {
    title: _t('Service overview'),
    subtitle: _t('Summarize key services'),
    icon: 'services'
  },
  hw_sw_inventory: {
    title: _t('HW/SW inventory'),
    subtitle: _t('Summarize key hardware and software components'),
    icon: 'inventory'
  },
  alerts_notifications: {
    title: _t('Alerts & notifications'),
    subtitle: _t('Summarize alerts and notifications'),
    icon: 'alerts'
  },
  event_stats: {
    title: _t('Events'),
    subtitle: _t('Summarize events'),
    icon: 'event-console'
  },
  other: {
    title: _t('Other elements'),
    subtitle: _t('Display user messages, sidebar elements, text or embed a URL'),
    icon: 'static-text'
  }
}

export type DashboardWidgetWorkflowKey = keyof typeof dashboardWidgetWorkflows
