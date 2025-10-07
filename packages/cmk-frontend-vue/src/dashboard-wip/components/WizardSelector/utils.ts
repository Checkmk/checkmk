/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type DashboardWidgetWorkflowKey } from '@/dashboard-wip/components/WidgetWorkflow/WidgetWorkflowTypes.ts'
import type { WidgetContentType } from '@/dashboard-wip/types/widget.ts'

export function widgetTypeToSelectorMatcher(
  widgetContentType: WidgetContentType
): DashboardWidgetWorkflowKey {
  switch (widgetContentType) {
    case 'combined_graph':
    case 'performance_graph':
    case 'barplot':
    case 'gauge':
    case 'single_metric':
    case 'average_scatterplot':
    case 'single_timeseries': {
      return 'metrics_graphs'
    }

    case 'custom_graph': {
      return 'custom_graphs'
    }

    case 'linked_view':
    case 'embedded_view': {
      return 'views'
    }

    case 'site_overview': {
      return 'host_site_overview'
    }

    default: {
      throw new Error(
        `No selector defined widget content type: ${widgetContentType}. Please add it.`
      )
    }
  }
}
