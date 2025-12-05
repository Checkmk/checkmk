#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import assert_never

from cmk.shared_typing.unified_search import IconNames, ProviderName

_MONITORING_ICONS: dict[str, IconNames] = {
    "applications": IconNames.topic_applications,
    "event_console": IconNames.topic_events,
    "history": IconNames.topic_history,
    "host_name": IconNames.topic_hosts,
    "host_group": IconNames.main_monitoring_active,
    "hostalias": IconNames.topic_hosts,
    "hwsw_inventory": IconNames.topic_inventory,
    "it_infrastructure_efficiency": IconNames.topic_analyze,
    "monitor": IconNames.main_monitoring_active,
    "other": IconNames.topic_other,
    "overview": IconNames.topic_overview,
    "problems": IconNames.topic_problems,
    "hostservice_search": IconNames.main_search,
    "service_description": IconNames.topic_services,
    "synthetic_monitoring": IconNames.synthetic_monitoring_topic,
    "system": IconNames.topic_system,
}

_CUSTOMIZE_ICONS: dict[str, IconNames] = {
    "business_reporting": IconNames.topic_reporting,
    "general": IconNames.topic_general,
    "graphs": IconNames.topic_graphs,
    "visualization": IconNames.topic_visualization,
}

_SETUP_ICONS: dict[str, IconNames] = {
    "access_to_agents": IconNames.main_setup_active,
    "agents": IconNames.topic_agents,
    "agent_rules": IconNames.topic_agents,
    "business_inteligence": IconNames.topic_bi,
    "deprecated_rulesets": IconNames.main_setup_active,
    "enforced_services": IconNames.topic_services,
    "event_console_rule_packs": IconNames.main_setup_active,
    "event_console_rules": IconNames.topic_events,
    "event_console_settings": IconNames.main_setup_active,
    "events": IconNames.topic_events,
    "exporter": IconNames.topic_exporter,
    "general": IconNames.topic_general,
    "global_settings": IconNames.topic_general,
    "host_monitoring_rules": IconNames.topic_hosts,
    "hosts": IconNames.topic_hosts,
    "http_tcp_email_": IconNames.topic_services,
    "hwsw_inventory": IconNames.topic_inventory,
    "maintenance": IconNames.topic_maintenance,
    "miscellaneous": IconNames.main_setup_active,
    "notification_parameter": IconNames.main_setup_active,
    "other_integrations": IconNames.topic_agents,
    "other_services": IconNames.topic_services,
    "quick_setup": IconNames.topic_quick_setups,
    "services": IconNames.topic_services,
    "service_discovery_rules": IconNames.main_setup_active,
    "service_monitoring_rules": IconNames.topic_services,
    "setup": IconNames.main_setup_active,
    "snmp_rules": IconNames.topic_agents,
    "synthetic_monitoring": IconNames.synthetic_monitoring_topic,
    "users": IconNames.topic_users,
    "vm_cloud_container": IconNames.topic_agents,
}

_HELP_ICONS: dict[str, IconNames] = {
    "learning_checkmk": IconNames.learning_checkmk,
    "developer_resources": IconNames.developer_resources,
    "ideas_portal": IconNames.lightbulb,
    "about_checkmk": IconNames.about_checkmk,
}

_USER_ICONS: dict[str, IconNames] = {
    "user_interface": IconNames.topic_user_interface,
    "user_messages": IconNames.topic_events,
    "user_profile": IconNames.topic_profile,
}


def _normalize_topic(topic: str) -> str:
    topic_normalized = topic.lower()
    topic_normalized = topic_normalized.replace(" ", "_")
    topic_normalized = re.sub(r"[^a-zA-Z0-9_]+", "", topic_normalized)
    return topic_normalized


def get_icon_for_topic(topic: str, provider: ProviderName) -> IconNames:
    normalized_topic = _normalize_topic(topic)

    mapping: dict[str, IconNames]
    default_icon: IconNames

    if provider == ProviderName.monitoring:
        mapping = _MONITORING_ICONS
        default_icon = IconNames.main_monitoring_active
    elif provider == ProviderName.setup:
        mapping = _SETUP_ICONS
        default_icon = IconNames.main_setup_active
    elif provider == ProviderName.customize:
        mapping = _CUSTOMIZE_ICONS
        default_icon = IconNames.main_customize_active
    else:
        assert_never(provider)

    return mapping.get(normalized_topic, default_icon)
