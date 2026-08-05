#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# List of modules for main menu and Setup snapin. These modules are
# defined in a plug-in because they contain cmk.gui.i18n strings.
# fields: mode, title, icon, permission, help

import time
from collections.abc import Iterable, Sequence
from typing import override

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import DynamicIcon, IconNames, StaticIcon
from cmk.gui.utils.loading_transition import LoadingTransition
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic
from cmk.web.utils.urls import makeuri_contextless, makeuri_contextless_rulespec_group

from ._main_module_topics import (
    MainModuleTopicAgents,
    MainModuleTopicEvents,
    MainModuleTopicGeneral,
    MainModuleTopicHosts,
    MainModuleTopicMaintenance,
    MainModuleTopicServices,
    MainModuleTopicUsers,
)


def register(main_module_registry: MainModuleRegistry) -> None:
    """Register Setup main modules common to all editions."""
    main_module_registry.register(MainModuleFolder)
    main_module_registry.register(MainModuleTags)
    main_module_registry.register(MainModuleGlobalSettings)
    main_module_registry.register(MainModuleReadOnly)
    main_module_registry.register(MainModuleRuleSearch)
    main_module_registry.register(MainModulePredefinedConditions)
    main_module_registry.register(MainModuleHostAndServiceParameters)
    main_module_registry.register(MainModuleHWSWInventory)
    main_module_registry.register(MainModuleNetworkingServices)
    main_module_registry.register(MainModuleOtherServices)
    main_module_registry.register(MainModuleCheckPlugins)
    main_module_registry.register(MainModuleHostGroups)
    main_module_registry.register(MainModuleHostCustomAttributes)
    main_module_registry.register(MainModuleServiceGroups)
    main_module_registry.register(MainModuleUsers)
    main_module_registry.register(MainModuleUserCustomAttributes)
    main_module_registry.register(MainModuleContactGroups)
    main_module_registry.register(MainModuleNotifications)
    main_module_registry.register(MainModuleAnalyzeNotifications)
    main_module_registry.register(MainModuleTestNotifications)
    main_module_registry.register(MainModuleTimeperiods)
    main_module_registry.register(MainModulePasswords)
    main_module_registry.register(MainModuleAuditLog)
    main_module_registry.register(MainModuleAnalyzeConfig)
    main_module_registry.register(MainModuleCertificateOverview)
    main_module_registry.register(MainModuleDiagnostics)
    main_module_registry.register(MainModulePerformanceProfiles)
    main_module_registry.register(MainModuleMonitoringRules)
    main_module_registry.register(MainModuleDiscoveryRules)
    main_module_registry.register(MainModuleEnforcedServices)
    main_module_registry.register(MainModuleAgentRules)
    main_module_registry.register(MainModuleOtherAgents)
    main_module_registry.register(MainModuleAgentAccessRules)
    main_module_registry.register(MainModuleSNMPRules)
    main_module_registry.register(MainModuleVMCloudContainer)
    main_module_registry.register(MainModuleOtherIntegrations)


def register_multisite_modules(main_module_registry: MainModuleRegistry) -> None:
    """Register Setup modules not available in the cloud edition."""
    main_module_registry.register(MainModuleRoles)
    main_module_registry.register(MainModuleLDAP)
    main_module_registry.register(MainModuleSites)


def register_agent_download_pages(main_module_registry: MainModuleRegistry) -> None:
    """Register built-in agent download pages for editions without the Agent Bakery."""
    main_module_registry.register(MainModuleAgentsWindows)
    main_module_registry.register(MainModuleAgentsLinux)


class MainModuleFolder(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "folder"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("Hosts")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.folder)

    @property
    @override
    def permission(self) -> None | str:
        return "hosts"

    @property
    @override
    def description(self) -> str:
        return _("Manage monitored hosts and services and the hosts' folder structure.")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleTags(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "tags"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("Tags")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.tag)

    @property
    @override
    def permission(self) -> None | str:
        # The module was renamed from hosttags to tags during 1.6 development. The permission can not
        # be changed easily for compatibility reasons. Leave old internal name for simplicity.
        return "hosttags"

    @property
    @override
    def description(self) -> str:
        return _("Tags can be used to classify hosts and services in a flexible way.")

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleGlobalSettings(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "globalvars"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Global settings")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.configuration)

    @property
    @override
    def permission(self) -> None | str:
        return "global"

    @property
    @override
    def description(self) -> str:
        return _(
            "Global settings for Checkmk, graphical user interface (GUI) and the monitoring core."
        )

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False

    @property
    @override
    def loading_transition(self) -> LoadingTransition | None:
        return LoadingTransition.catalog


class MainModuleReadOnly(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "read_only"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Read only mode")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.read_only)

    @property
    @override
    def permission(self) -> None | str:
        return "read_only"

    @property
    @override
    def description(self) -> str:
        return _("Set the Checkmk configuration interface to read only mode for maintenance.")

    @property
    @override
    def sort_index(self) -> int:
        return 20

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleRuleSearch(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "rule_search"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Rule search")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.search)  # TODO: this is a new icon!

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Search all rules and rule sets")

    @property
    @override
    def sort_index(self) -> int:
        return 5

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModulePredefinedConditions(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "predefined_conditions"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Predefined conditions")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.predefined_conditions)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Use predefined conditions to centralize the conditions of your rule sets.")

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleHostAndServiceParameters(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "host_monconf")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("Host monitoring rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(
            IconNames.folder,
            emblem="rulesets",
        )

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Check parameters and other configuration variables for hosts")

    @property
    @override
    def sort_index(self) -> int:
        return 20

    @property
    @override
    def is_show_more(self) -> bool:
        return False

    @property
    @override
    def loading_transition(self) -> LoadingTransition | None:
        return LoadingTransition.catalog


class MainModuleHWSWInventory(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "inventory")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("HW/SW inventory rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.inventory)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Manage hard- and software inventory related rule sets")

    @property
    @override
    def sort_index(self) -> int:
        return 60

    @property
    @override
    def is_show_more(self) -> bool:
        return True

    @classmethod
    @override
    def main_menu_search_terms(cls) -> Sequence[str]:
        return ["hardware", "software"]


class MainModuleNetworkingServices(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "activechecks")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("HTTP, TCP, email, ...")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.network_services)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _(
            "Configure monitoring of networking services using classical Nagios plug-ins"
            " (so called active checks)"
        )

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleOtherServices(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "custom_checks")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Other services")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.nagios)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _(
            "Integrate [active_checks#mrpe|custom nagios plug-ins] into the "
            "monitoring as active checks."
        )

    @property
    @override
    def sort_index(self) -> int:
        return 40

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleCheckPlugins(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "check_plugins"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Catalog of check plug-ins")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.check_plugins)

    @property
    @override
    def permission(self) -> None | str:
        return "check_plugins"

    @property
    @override
    def description(self) -> str:
        return _("Browse the catalog of all check plug-ins, create static checks")

    @property
    @override
    def sort_index(self) -> int:
        return 70

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleHostGroups(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "host_groups"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("Host groups")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.hostgroups)

    @property
    @override
    def permission(self) -> None | str:
        return "groups"

    @property
    @override
    def description(self) -> str:
        return _("Organize your hosts in groups independent of the tree structure.")

    @property
    @override
    def sort_index(self) -> int:
        return 50

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleHostCustomAttributes(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "host_attrs"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    @override
    def title(self) -> str:
        return _("Custom host attributes")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.custom_attr)

    @property
    @override
    def permission(self) -> None | str:
        return "custom_attributes"

    @property
    @override
    def description(self) -> str:
        return _("Create your own host related attributes")

    @property
    @override
    def sort_index(self) -> int:
        return 55

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleServiceGroups(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "service_groups"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Service groups")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.servicegroups)

    @property
    @override
    def permission(self) -> None | str:
        return "groups"

    @property
    @override
    def description(self) -> str:
        return _("Organize your services in groups")

    @property
    @override
    def sort_index(self) -> int:
        return 60

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleUsers(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "users"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    @override
    def title(self) -> str:
        return _("Users")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.users)

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("Manage users of the monitoring system.")

    @property
    @override
    def sort_index(self) -> int:
        return 20

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleRoles(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "roles"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    @override
    def title(self) -> str:
        return _("Roles & permissions")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.roles)

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("User roles are configurable sets of permissions.")

    @property
    @override
    def sort_index(self) -> int:
        return 40

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleLDAP(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "ldap_config"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    @override
    def title(self) -> str:
        return _("LDAP & Active Directory")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.ldap)

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("Connect Checkmk with your LDAP or Active Directory to create users in Checkmk.")

    @property
    @override
    def sort_index(self) -> int:
        return 50

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleUserCustomAttributes(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "user_attrs"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    @override
    def title(self) -> str:
        return _("Custom user attributes")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.custom_attr)

    @property
    @override
    def permission(self) -> None | str:
        return "custom_attributes"

    @property
    @override
    def description(self) -> str:
        return _("Create your own user related attributes")

    @property
    @override
    def sort_index(self) -> int:
        return 55

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleContactGroups(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "contact_groups"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    @override
    def title(self) -> str:
        return _("Contact groups")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.contactgroups)

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("Contact groups are used to assign users to hosts and services")

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleNotifications(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "notifications"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    @override
    def title(self) -> str:
        return _("Notifications")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.notifications)

    @property
    @override
    def permission(self) -> None | str:
        return "notifications"

    @property
    @override
    def description(self) -> str:
        return _("Rules for the notification of contacts about host and service problems")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleAnalyzeNotifications(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "analyze_notifications"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    @override
    def title(self) -> str:
        return _("Analyze recent notifications")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.analyze)

    @property
    @override
    def permission(self) -> None | str:
        return "notifications"

    @property
    @override
    def description(self) -> str:
        return _("Analyze recent notifications with your current rule set")

    @property
    @override
    def sort_index(self) -> int:
        return 11

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleTestNotifications(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "test_notifications"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    @override
    def title(self) -> str:
        return _("Test notifications")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.analysis)

    @property
    @override
    def permission(self) -> None | str:
        return "notifications"

    @property
    @override
    def description(self) -> str:
        return _("Test custom notifications with your current rule set")

    @property
    @override
    def sort_index(self) -> int:
        return 12

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleTimeperiods(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "timeperiods"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Time periods")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.timeperiods)

    @property
    @override
    def permission(self) -> None | str:
        return "timeperiods"

    @property
    @override
    def description(self) -> str:
        return _(
            "Time periods restrict notifications and other things to certain periods of the day."
        )

    @property
    @override
    def sort_index(self) -> int:
        return 40

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleSites(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "sites"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Distributed monitoring")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.sites)

    @property
    @override
    def permission(self) -> None | str:
        return "sites"

    @property
    @override
    def description(self) -> str:
        return _("Distributed monitoring using multiple Checkmk sites")

    @property
    @override
    def sort_index(self) -> int:
        return 70

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModulePasswords(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "passwords"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Passwords")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)

    @property
    @override
    def permission(self) -> None | str:
        return "passwords"

    @property
    @override
    def description(self) -> str:
        return _("Store and share passwords for later use in checks.")

    @property
    @override
    def sort_index(self) -> int:
        return 50

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleAuditLog(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "auditlog"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Audit log")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.auditlog)

    @property
    @override
    def permission(self) -> None | str:
        return "auditlog"

    @property
    @override
    def description(self) -> str:
        return _("Examine the change history of the configuration")

    @property
    @override
    def sort_index(self) -> int:
        return 80

    @property
    @override
    def is_show_more(self) -> bool:
        return True

    @property
    @override
    def loading_transition(self) -> LoadingTransition | None:
        return LoadingTransition.table


class MainModuleAnalyzeConfig(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "analyze_config"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    @override
    def title(self) -> str:
        return _("Analyze configuration")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.analyze_config)

    @property
    @override
    def permission(self) -> None | str:
        return "analyze_config"

    @property
    @override
    def description(self) -> str:
        return _("See hints how to improve your Checkmk installation")

    @property
    @override
    def sort_index(self) -> int:
        return 40

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleCertificateOverview(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "certificate_overview"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    @override
    def title(self) -> str:
        return _("Certificate overview")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.certificate)

    @property
    @override
    def permission(self) -> None | str:
        return "certificate_overview"

    @property
    @override
    def description(self) -> str:
        return _("Displays details of the certificates used by Checkmk")

    @property
    @override
    def sort_index(self) -> int:
        return 35

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleDiagnostics(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "diagnostics"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    @override
    def title(self) -> str:
        return _("Support diagnostics")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        loc_time = time.localtime()
        if loc_time.tm_hour == 13 and loc_time.tm_min == 37:
            return StaticIcon(IconNames.d146n0571c5)
        return StaticIcon(IconNames.diagnostics)

    @property
    @override
    def permission(self) -> None | str:
        return "diagnostics"

    @property
    @override
    def description(self) -> str:
        return _("Collect information of Checkmk sites for diagnostic analysis.")

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModulePerformanceProfiles(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "performance_profiles"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    @override
    def title(self) -> str:
        return _("Performance profiles")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.diagnostics)

    @property
    @override
    def permission(self) -> None | str:
        return "performance_profiles"

    @property
    @override
    def description(self) -> str:
        return _("View stored performance profiles and flamegraphs for analysis.")

    @property
    @override
    def sort_index(self) -> int:
        return 31

    @property
    @override
    def is_show_more(self) -> bool:
        return True

    @property
    @override
    def enabled(self) -> bool:
        return bool(active_config.profiling_options.get("enabled", False))


class MainModuleMonitoringRules(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "monconf")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Service monitoring rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(
            IconNames.services,
            emblem="rulesets",
        )

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Service monitoring rules")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False

    @property
    @override
    def loading_transition(self) -> LoadingTransition | None:
        return LoadingTransition.catalog


class MainModuleDiscoveryRules(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "checkparams")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Discovery rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.service_discovery)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Discovery settings")

    @property
    @override
    def sort_index(self) -> int:
        return 20

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleEnforcedServices(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "static")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    @override
    def title(self) -> str:
        return _("Enforced services")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.static_checks)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Configure enforced checks without using service discovery")

    @property
    @override
    def sort_index(self) -> int:
        return 25

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleAgentsWindows(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "download_agents_windows"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Windows")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.download_agents)

    @property
    @override
    def permission(self) -> None | str:
        return "download_agents"

    @property
    @override
    def description(self) -> str:
        return _("Downloads Checkmk agent and plug-ins for Windows")

    @property
    @override
    def sort_index(self) -> int:
        return 15

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentsLinux(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "download_agents_linux"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Linux")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.download_agents)

    @property
    @override
    def permission(self) -> None | str:
        return "download_agents"

    @property
    @override
    def description(self) -> str:
        return _("Downloads Checkmk agent and plug-ins for Linux")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentRules(ABCMainModule):
    @property
    @override
    def enabled(self) -> bool:
        return False

    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "agents")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Agent rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(
            IconNames.agents,
            emblem="rulesets",
        )

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Configuration of monitoring agents for Linux, Windows and Unix")

    @property
    @override
    def sort_index(self) -> int:
        return 80

    @property
    @override
    def is_show_more(self) -> bool:
        return True

    @classmethod
    @override
    def additional_breadcrumb_items(cls) -> Iterable[BreadcrumbItem]:
        yield BreadcrumbItem(
            title="Windows, Linux, Solaris, AIX",
            url=makeuri_contextless(
                request,
                [("mode", "agents")],
                filename="wato.py",
            ),
            id="agents",
        )


class MainModuleOtherAgents(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "download_agents"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Other operating systems")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.os_other)

    @property
    @override
    def permission(self) -> None | str:
        return "download_agents"

    @property
    @override
    def description(self) -> str:
        return _("Downloads Checkmk agents for other operating systems")

    @property
    @override
    def sort_index(self) -> int:
        return 20

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentAccessRules(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "agent")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Agent access rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(
            IconNames.agents,
            emblem="rulesets",
        )

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Configure agent access related settings using rule sets")

    @property
    @override
    def sort_index(self) -> int:
        return 60

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleSNMPRules(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "snmp")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("SNMP rules")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.snmp)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Configure SNMP related settings using rule sets")

    @property
    @override
    def sort_index(self) -> int:
        return 70

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleVMCloudContainer(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "vm_cloud_container")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("VM, cloud, container")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.cloud)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Integrate with VM, cloud or container platforms")

    @property
    @override
    def sort_index(self) -> int:
        return 30

    @property
    @override
    def is_show_more(self) -> bool:
        return False


class MainModuleOtherIntegrations(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "datasource_programs")

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    @override
    def title(self) -> str:
        return _("Other integrations")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.integrations_other)

    @property
    @override
    def permission(self) -> None | str:
        return "rulesets"

    @property
    @override
    def description(self) -> str:
        return _("Monitoring of applications such as processes, services or databases")

    @property
    @override
    def sort_index(self) -> int:
        return 40

    @property
    @override
    def is_show_more(self) -> bool:
        return False
