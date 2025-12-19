/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon, EmblemIcon, IconNames } from 'cmk-shared-typing/typescript/icon'

const _MONITORING_ICONS: Record<string, [IconNames, IconNames | EmblemIcon]> = {
  applications: ['topic-applications', 'topic-applications'],
  event_console: ['topic-events', 'topic-events'],
  history: ['topic-history', 'topic-history'],
  host_name: ['topic-hosts', 'folder'],
  hosts: ['topic-hosts', 'folder'],
  host_group: ['main-monitoring-active', 'hostgroups'],
  hostalias: ['topic-hosts', 'folder'],
  hwsw_inventory: ['topic-inventory', 'topic-inventory'],
  it_infrastructure_efficiency: ['topic-analyze', 'topic-analyze'],
  monitor: ['main-monitoring-active', 'main-monitoring'],
  other: ['topic-other', 'topic-other'],
  overview: ['topic-overview', 'topic-overview'],
  problems: ['topic-problems', 'topic-problems'],
  hostservice_search: ['main-search', 'main-search'],
  service_description: ['topic-services', 'topic-services'],
  synthetic_monitoring: ['synthetic-monitoring-topic', 'synthetic-monitoring-topic'],
  system: ['topic-system', 'topic-system']
}

const _CUSTOMIZE_ICONS: Record<string, [IconNames, IconNames | EmblemIcon]> = {
  business_reporting: ['topic-reporting', 'topic-reporting'],
  general: ['topic-general', 'topic-general'],
  graphs: ['topic-graphs', 'topic-graphs'],
  visualization: ['topic-visualization', 'topic-visualization']
}

const _SETUP_ICONS: Record<string, [IconNames, IconNames | EmblemIcon]> = {
  access_to_agents: ['main-setup-active', 'main-setup'],
  agents: ['topic-agents', 'topic-agents'],
  agent_rules: [
    'topic-agents',
    { type: 'emblem_icon', icon: { type: 'default_icon', id: 'agents' }, emblem: 'rulesets' }
  ],
  business_inteligence: ['topic-bi', 'aggr'],
  deprecated_rulesets: ['main-setup-active', 'main-setup'],
  enforced_services: ['topic-services', 'static-checks'],
  event_console_rule_packs: ['main-setup-active', 'main-setup'],
  event_console_rules: [
    'topic-events',
    { type: 'emblem_icon', icon: { type: 'default_icon', id: 'event-console' }, emblem: 'rulesets' }
  ],
  event_console_settings: ['main-setup-active', 'main-setup'],
  events: ['topic-events', 'event-console'],
  exporter: ['topic-exporter', 'topic-exporter'],
  general: ['topic-general', 'topic-general'],
  global_settings: ['topic-general', 'configuration'],
  host_monitoring_rules: ['topic-hosts', 'folder'],
  hosts: ['topic-hosts', 'folder'],
  http_tcp_email_: ['topic-services', 'network-services'],
  hwsw_inventory: ['topic-inventory', 'inventory'],
  maintenance: ['topic-maintenance', 'topic-maintenance'],
  miscellaneous: ['main-setup-active', 'main-setup-active'],
  notification_parameter: ['main-setup-active', 'main-setup'],
  other_integrations: ['topic-agents', 'integrations-other'],
  other_services: ['topic-services', 'nagios'],
  quick_setup: ['topic-quick-setups', 'topic-quick-setups'],
  services: ['topic-services', 'topic-services'],
  service_discovery_rules: ['main-setup-active', 'service-discovery'],
  service_monitoring_rules: [
    'topic-services',
    { type: 'emblem_icon', icon: { type: 'default_icon', id: 'services' }, emblem: 'rulesets' }
  ],
  setup: ['main-setup-active', 'main-setup'],
  snmp_rules: ['topic-agents', 'snmp'],
  synthetic_monitoring: ['synthetic-monitoring-topic', 'synthetic-monitoring-topic'],
  users: ['topic-users', 'users'],
  vm_cloud_container: ['topic-agents', 'cloud']
}

function normalizeTopic(topic: string): string {
  let topicNormalized = topic.toLowerCase()
  topicNormalized = topicNormalized.replace(/ /g, '_')
  topicNormalized = topicNormalized.replace(/[^a-zA-Z0-9_]+/g, '')
  return topicNormalized
}

function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`)
}

export function getIconForTopic(
  topic: string,
  provider: string,
  iconsPerItem: boolean
): DynamicIcon {
  const normalizedTopic = normalizeTopic(topic)

  let mapping: Record<string, [IconNames, IconNames | EmblemIcon]>
  let defaultIcon: [IconNames, IconNames | EmblemIcon]

  if (provider === 'monitoring') {
    mapping = _MONITORING_ICONS
    defaultIcon = ['main-monitoring-active', 'main-monitoring']
  } else if (provider === 'setup') {
    mapping = _SETUP_ICONS
    defaultIcon = ['main-setup-active', 'main-setup']
  } else if (provider === 'customize') {
    mapping = _CUSTOMIZE_ICONS
    defaultIcon = ['main-customize-active', 'main-customize']
  } else {
    assertNever(provider as never)
  }

  const icon = (mapping[normalizedTopic] ? mapping[normalizedTopic] : defaultIcon)[
    iconsPerItem ? 1 : 0
  ]

  if (typeof icon === 'string') {
    return { type: 'default_icon', id: icon }
  }

  return icon
}
