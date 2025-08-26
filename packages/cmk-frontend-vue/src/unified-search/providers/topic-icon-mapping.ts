/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ProviderTopicIconMapping } from './search-utils.types'

// null values defaults to provider icons

export const topicIconMapping: ProviderTopicIconMapping = {
  monitoring: {
    applications: 'applications',
    event_console: 'events',
    history: 'history',
    host_name: 'host',
    host_group: null,
    hostalias: 'host',
    hwsw_inventory: 'inventory',
    it_infrastructure_efficiency: 'analyze',
    monitor: null, // can be replaced after topic rewrite in the BE is removed
    other: 'other',
    overview: 'overview',
    problems: 'problems',
    hostservice_search: 'search',
    service_description: 'services',
    synthetic_monitoring: 'synthetic-monitoring',
    system: 'system'
  },
  customize: {
    business_reporting: 'reporting',
    general: 'general',
    graphs: 'graphs',
    visualization: 'visualization'
  },
  setup: {
    access_to_agents: null,
    agents: 'agents',
    agent_rules: 'agents',
    business_inteligence: 'bi',
    deprecated_rulesets: null,
    enforced_services: 'services',
    event_console_rule_packs: null,
    event_console_rules: 'events',
    event_console_settings: null,
    events: 'events',
    exporter: 'exporter',
    general: 'general',
    global_settings: 'general',
    host_monitoring_rules: 'host',
    hosts: 'host',
    http_tcp_email_: 'services',
    hwsw_inventory: 'inventory',
    maintenance: 'maintenance',
    miscellaneous: null,
    notification_parameter: null,
    other_integrations: 'agents',
    other_services: 'services',
    quick_setup: 'quick-setups',
    services: 'services',
    service_discovery_rules: null,
    service_monitoring_rules: 'services',
    setup: null, // can be replaced after topic rewrite in the BE is removed
    snmp_rules: 'agents',
    synthetic_monitoring: 'synthetic-monitoring',
    users: 'users',
    vm_cloud_container: 'agents'
  }
}
