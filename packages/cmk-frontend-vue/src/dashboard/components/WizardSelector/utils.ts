/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type DashboardWidgetWorkflowKey } from '@/dashboard/components/WidgetWorkflow/WidgetWorkflowTypes.ts'
import type { WidgetContentType } from '@/dashboard/types/widget.ts'

// null: the widget has no editor yet
export function widgetTypeToSelectorMatcher(
  widgetContentType: WidgetContentType
): DashboardWidgetWorkflowKey | null {
  switch (widgetContentType) {
    case 'combined_graph':
    case 'performance_graph':
    case 'barplot':
    case 'gauge':
    case 'single_metric':
    case 'average_scatterplot':
    case 'top_list':
    case 'single_timeseries': {
      return 'metrics_graphs'
    }

    case 'custom_graph': {
      return 'link_custom_graph'
    }

    // edited in the Clone and Create workflows, which are not implemented yet
    // Clone: CMK-39219; Create: CMK-39220
    case 'embedded_custom_graph': {
      return null
    }

    case 'linked_view':
    case 'embedded_view': {
      return 'views'
    }

    case 'host_stats':
    case 'host_state':
    case 'host_state_summary':
    case 'site_overview': {
      return 'host_site_overview'
    }

    case 'service_state':
    case 'service_state_summary':
    case 'service_stats': {
      return 'service_overview'
    }

    case 'event_stats': {
      return 'event_stats'
    }

    case 'url':
    case 'static_text':
    case 'sidebar_element':
    case 'user_messages': {
      return 'other'
    }

    case 'notification_timeline':
    case 'alert_overview':
    case 'alert_timeline':
    case 'problem_graph': {
      return 'alerts_notifications'
    }

    case 'inventory': {
      return 'hw_sw_inventory'
    }

    case 'ntop_alerts':
    case 'ntop_flows':
    case 'ntop_top_talkers': {
      return 'ntop'
    }

    case 'monitoring_table': {
      return null
    }

    default: {
      throw new Error(
        `No selector defined widget content type: ${widgetContentType}. Please add it.`
      )
    }
  }
}

export function wizardSlideInSize(wizard: string): 'small' | 'medium' | 'large' {
  if (['other', 'ntop'].includes(wizard)) {
    return 'small'
  }
  if (wizard === 'views') {
    return 'large'
  }
  return 'medium'
}
