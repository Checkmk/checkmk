/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ProviderTopicIconMapping } from './search-utils.types'

// null values defaults to provider icons

export const topicIconMapping: ProviderTopicIconMapping = {
  monitoring: {
    applications: 'topic-applications',
    event_console: 'topic-events',
    history: 'topic-history',
    host_name: 'topic-host',
    host_group: 'main-monitoring-active',
    hostalias: 'topic-host',
    hwsw_inventory: 'topic-inventory',
    it_infrastructure_efficiency: 'topic-analyze',
    monitor: 'main-monitoring-active', // can be replaced after topic rewrite in the BE is removed
    other: 'topic-other',
    overview: 'topic-overview',
    problems: 'topic-problems',
    hostservice_search: 'topic-search',
    service_description: 'topic-services',
    synthetic_monitoring: 'topic-synthetic-monitoring',
    system: 'topic-system'
  },
  customize: {
    business_reporting: 'topic-reporting',
    general: 'topic-general',
    graphs: 'topic-graphs',
    visualization: 'topic-visualization'
  },
  setup: {
    access_to_agents: 'main-setup-active',
    agents: 'topic-agents',
    agent_rules: 'topic-agents',
    business_inteligence: 'topic-bi',
    deprecated_rulesets: 'main-setup-active',
    enforced_services: 'topic-services',
    event_console_rule_packs: 'main-setup-active',
    event_console_rules: 'topic-events',
    event_console_settings: 'main-setup-active',
    events: 'topic-events',
    exporter: 'topic-exporter',
    general: 'topic-general',
    global_settings: 'topic-general',
    host_monitoring_rules: 'topic-host',
    hosts: 'topic-host',
    http_tcp_email_: 'topic-services',
    hwsw_inventory: 'topic-inventory',
    maintenance: 'topic-maintenance',
    miscellaneous: 'main-setup-active',
    notification_parameter: 'main-setup-active',
    other_integrations: 'topic-agents',
    other_services: 'topic-services',
    quick_setup: 'topic-quick-setups',
    services: 'topic-services',
    service_discovery_rules: 'main-setup-active',
    service_monitoring_rules: 'topic-services',
    setup: 'main-setup-active', // can be replaced after topic rewrite in the BE is removed
    snmp_rules: 'topic-agents',
    synthetic_monitoring: 'topic-synthetic-monitoring',
    users: 'topic-users',
    vm_cloud_container: 'topic-agents'
  }
}
