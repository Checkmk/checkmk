#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""References into the Checkmk documentation, youtube channel and werk list.

These need to know the running edition, so they stay out of the generic URL
helpers in cmk.web.utils.urls.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import cmk.utils.paths
from cmk.ccc.version import __version__, Edition, edition, Version
from cmk.web.utils.urls import urlencode_vars


class DocReference(Enum):
    """All references to the documentation - e.g. "[intro_setup#install|Welcome]" - must be listed
    in DocReference. The string must consist of the page name and if an anchor exists the anchor
    name joined by a '#'. E.g. INTRO_SETUP_INSTALL = "intro_setup#install"""

    ACTIVE_CHECKS = "active_checks"
    ACTIVE_CHECKS_MRPE = "active_checks#mrpe"
    AGENT_LINUX = "agent_linux"
    AGENT_WINDOWS = "agent_windows"
    AGENT_LINUX_LEGACY = "agent_linux_legacy"
    ALERT_HANDLERS = "alert_handlers"
    ANALYZE_CONFIG = "analyze_configuration"
    ANALYZE_NOTIFICATIONS = "notifications#_rule_evaluation_by_the_notification_module"
    AWS = "monitoring_aws"
    AWS_MANUAL_VM = "monitoring_aws#_manually_creating_hosts_for_ec2_instances"
    AZURE = "monitoring_azure"
    BACKUPS = "backup"
    BI = "bi"  # Business Intelligence
    BOOKMARK_LIST = "user_interface#bookmarks"
    CERTIFICATES = "certificates"
    COMMANDS = "commands"
    COMMANDS_ACK = "basics_ackn"
    COMMANDS_DOWNTIME = "basics_downtimes"
    CUSTOM_GRAPH = "graphing#custom_graphs"
    DASHBOARD_HOST_PROBLEMS = "dashboards#host_problems"
    DASHBOARDS = "dashboards"
    DCD = "dcd"  # dynamic host configuration
    DEVEL_CHECK_PLUGINS = "devel_intro"
    DIAGNOSTICS = "support_diagnostics"
    DIAGNOSTICS_CLI = "support_diagnostics#commandline"
    DISTRIBUTED_MONITORING = "distributed_monitoring"
    EVENTCONSOLE = "ec"
    FORECAST_GRAPH = "forecast_graphs"
    FINETUNING_MONITORING = "intro_finetune"
    GCP = "monitoring_gcp"
    GCP_MANUAL_VM = "monitoring_gcp#_manually_creating_hosts_for_vm_instances"
    GRAPHING_RRDS = "graphing#rrds"
    HOST_TAGS = "host_tags"
    HOSTS_STRUCTURE = "hosts_structure"
    INFLUXDB_CONNECTIONS = "metrics_exporter"
    INTRO_BESTPRACTICE = "intro_bestpractise"
    INTRO_CREATING_FOLDERS = "intro_setup_monitor#folders"
    INTRO_FOLDERS = "intro_setup_monitor#folders"  # noqa: PIE796 # keep duplicate; values may diverge
    INTRO_GUI = "intro_gui"
    INTRO_LINUX = "intro_setup_monitor#linux"
    INTRO_SERVICES = "intro_setup_monitor#services"
    INTRO_WELCOME = "welcome"
    INTRO_SETUP = "intro_setup"
    INTRO_USERS = "intro_users"
    INTRO_NOTIFICATIONS = "intro_notifications"
    KUBERNETES = "monitoring_kubernetes"
    LICENSING = "license"
    LDAP = "ldap"
    MKPS = "mkps"
    NOTIFICATIONS = "notifications"
    NTOPNG_CONNECT = "ntop#ntop_connect"
    PIGGYBACK = "piggyback"
    PROMETHEUS = "monitoring_prometheus"
    REGEXES = "regexes"
    REPLACE_AGENT_SIGNATURE_KEYS = "agent_deployment#replacing_signature_keys"
    REST_API = "rest_api"
    REPORTS = "reporting"
    RELAY = "relay"
    SLA_CONFIGURATION = "sla"
    TIMEPERIODS = "timeperiods"
    TEST_NOTIFICATIONS = "notifications#notification_testing"
    USER_INTERFACE = "user_interface"
    VIEWS = "views"
    VMWARE = "monitoring_vmware"
    WATO_AGENTS = "wato_monitoringagents"
    WATO_AGENT_CMK = "wato_monitoringagents#agents"
    WATO_HOSTS = "wato_hosts"
    WATO_RULES = "wato_rules"
    WATO_RULES_DEPCRECATED = "wato_rules#obsolete_rule_sets"
    WATO_RULES_IN_USE = "wato_rules#_rule_sets_in_use"
    WATO_RULES_INEFFECTIVE = "wato_rules#ineffective_rules"
    WATO_RULES_LABELS = "wato_rules#_labels"
    WATO_SERVICES = "wato_services"
    WATO_SERVICES_ENFORCED_SERVICES = "wato_services#enforced_services"
    WATO_USER = "wato_user"
    WATO_USER_2FA = "wato_user#2fa"

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key in cls._member_names_


def get_docs_base_url(language: str) -> str:
    version = (
        "saas"
        if edition(cmk.utils.paths.omd_root) == Edition.CLOUD
        else Version.from_str(__version__).version_base or "master"
    )
    lang = "de" if language == "de" else "en"
    return f"https://docs.checkmk.com/{version}/{lang}"


@dataclass(frozen=True, kw_only=True)
class DocReferenceUtm:
    campaign: Literal["help_menu", "inline_help", "error_help", "setup_wizard", "dashboard"]
    content: str


def doc_reference_url(
    language: str,
    utm: DocReferenceUtm,
    doc_ref: DocReference | None = None,
) -> str:
    base = get_docs_base_url(language)
    version = Version.from_str(__version__).version_without_rc or "master"
    cmk_edition = edition(cmk.utils.paths.omd_root)
    query = urlencode_vars(
        [
            ("utm_source", "checkmk"),
            ("utm_medium", "app"),
            ("utm_campaign", utm.campaign),
            ("utm_content", utm.content),
            ("utm_term", f"{version}_{cmk_edition.short}"),
        ]
    )

    if doc_ref is None:
        return f"{base}?{query}"
    if "#" not in doc_ref.value:
        return f"{base}/{doc_ref.value}.html?{query}"
    page, anchor = doc_ref.value.split("#", 1)
    return f"{base}/{page}.html?{query}#{anchor}"


class YouTubeReference(Enum):
    """All references to youtube videos must be listed in YouTubeReference. The string must hold a
    valid video id."""

    INSTALLING_CHECKMK = "opO-SOgOJ1I"
    MONITORING_WINDOWS = "Nxiq7Jb9mB4"

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key in cls._member_names_


def youtube_reference_url(youtube_ref: YouTubeReference | None = None) -> str:
    # Default to the Checkmk youtube channel
    if youtube_ref is None:
        return "https://youtube.com/@checkmk-channel"
    return "https://youtu.be/%s" % youtube_ref.value


class WerkReference(Enum):
    DECOMMISSION_V1_API = 17201

    def ref(self) -> str:
        return f"Werk #{self.value}"


def werk_reference_url(werk: WerkReference) -> str:
    return f"https://checkmk.com/werk/{werk.value}"
