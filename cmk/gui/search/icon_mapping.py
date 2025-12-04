#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import assert_never

from .type_defs import Provider

_MONITORING_ICONS: dict[str, str] = {
    "applications": "topic-applications",
    "event_console": "topic-events",
    "history": "topic-history",
    "host_name": "topic-hosts",
    "host_group": "main-monitoring-active",
    "hostalias": "topic-hosts",
    "hwsw_inventory": "topic-inventory",
    "it_infrastructure_efficiency": "topic-analyze",
    "monitor": "main-monitoring-active",
    "other": "topic-other",
    "overview": "topic-overview",
    "problems": "topic-problems",
    "hostservice_search": "topic-search",
    "service_description": "topic-services",
    "synthetic_monitoring": "topic-synthetic-monitoring",
    "system": "topic-system",
}

_CUSTOMIZE_ICONS: dict[str, str] = {
    "business_reporting": "topic-reporting",
    "general": "topic-general",
    "graphs": "topic-graphs",
    "visualization": "topic-visualization",
}

_SETUP_ICONS: dict[str, str] = {
    "access_to_agents": "main-setup-active",
    "agents": "topic-agents",
    "agent_rules": "topic-agents",
    "business_inteligence": "topic-bi",
    "deprecated_rulesets": "main-setup-active",
    "enforced_services": "topic-services",
    "event_console_rule_packs": "main-setup-active",
    "event_console_rules": "topic-events",
    "event_console_settings": "main-setup-active",
    "events": "topic-events",
    "exporter": "topic-exporter",
    "general": "topic-general",
    "global_settings": "topic-general",
    "host_monitoring_rules": "topic-hosts",
    "hosts": "topic-hosts",
    "http_tcp_email_": "topic-services",
    "hwsw_inventory": "topic-inventory",
    "maintenance": "topic-maintenance",
    "miscellaneous": "main-setup-active",
    "notification_parameter": "main-setup-active",
    "other_integrations": "topic-agents",
    "other_services": "topic-services",
    "quick_setup": "topic-quick-setups",
    "services": "topic-services",
    "service_discovery_rules": "main-setup-active",
    "service_monitoring_rules": "topic-services",
    "setup": "main-setup-active",
    "snmp_rules": "topic-agents",
    "synthetic_monitoring": "topic-synthetic-monitoring",
    "users": "topic-users",
    "vm_cloud_container": "topic-agents",
}

_HELP_ICONS: dict[str, str] = {
    "learning_checkmk": "learning-checkmk",
    "developer_resources": "developer-resources",
    "ideas_portal": "lightbulb",
    "about_checkmk": "about-checkmk",
}

_USER_ICONS: dict[str, str] = {
    "user_interface": "topic-user-interface",
    "user_messages": "topic-events",
    "user_profile": "topic-profile",
}


def _normalize_topic(topic: str) -> str:
    topic_normalized = topic.lower()
    topic_normalized = topic_normalized.replace(" ", "_")
    topic_normalized = re.sub(r"[^a-zA-Z0-9_]+", "", topic_normalized)
    return topic_normalized


def get_icon_for_topic(topic: str, provider: Provider) -> str:
    normalized_topic = _normalize_topic(topic)

    mapping: dict[str, str]
    default_icon: str

    if provider == "monitoring":
        mapping = _MONITORING_ICONS
        default_icon = "main-monitoring-active"
    elif provider == "setup":
        mapping = _SETUP_ICONS
        default_icon = "main-setup-active"
    elif provider == "customize":
        mapping = _CUSTOMIZE_ICONS
        default_icon = "main-customize-active"
    else:
        assert_never(provider)

    return mapping.get(normalized_topic, default_icon)
