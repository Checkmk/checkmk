/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { IconEmblems, SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

const { _t } = usei18n()

export interface WorkflowItem {
  title: TranslatedString
  subtitle: TranslatedString

  icon: SimpleIcons
  icon_emblem?: IconEmblems | undefined

  unavailableReason?: TranslatedString | undefined
}

export interface WorkflowGroup extends WorkflowItem {
  subWorkflows: Record<string, WorkflowItem>
}

export type WorkflowCatalog = Record<string, WorkflowItem | WorkflowGroup>

export function isWorkflowGroup(workflow: WorkflowItem | undefined): workflow is WorkflowGroup {
  return workflow !== undefined && 'subWorkflows' in workflow
}

export function findParentWorkflowKey(
  catalog: WorkflowCatalog,
  workflowKey: string
): string | null {
  for (const [groupKey, workflow] of Object.entries(catalog)) {
    if (isWorkflowGroup(workflow) && Object.hasOwn(workflow.subWorkflows, workflowKey)) {
      return groupKey
    }
  }
  return null
}

export function getDashboardWidgetWorkflows(
  ntopActive: boolean = false,
  networkFlowActive: boolean = false
): WorkflowCatalog {
  const workflows: WorkflowCatalog = {
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

  if (ntopActive) {
    workflows['ntop'] = {
      title: _t('Ntop'),
      subtitle: _t('Display ntop alerts, flows or top talkers'),
      icon: 'ntop'
    }
  }
  if (networkFlowActive) {
    workflows['network_flow'] = {
      title: _t('Network flow monitoring'),
      subtitle: _t('Visualize network flow traffic, applications and autonomous systems'),
      icon: 'network-topology'
    }
  }
  return workflows
}

export type DashboardWidgetWorkflowKey =
  | 'metrics_graphs'
  | 'custom_graphs'
  | 'views'
  | 'host_site_overview'
  | 'service_overview'
  | 'hw_sw_inventory'
  | 'alerts_notifications'
  | 'event_stats'
  | 'other'
  | 'ntop'
  | 'network_flow'
