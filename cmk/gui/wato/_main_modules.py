#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# List of modules for main menu and Setup snapin. These modules are
# defined in a plug-in because they contain cmk.gui.i18n strings.
# fields: mode, title, icon, permission, help

import time
from collections.abc import Iterable, Sequence

import cmk.ccc.version as cmk_version

from cmk.utils import paths

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import Icon
from cmk.gui.utils.urls import makeuri_contextless, makeuri_contextless_rulespec_group
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic

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
    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CSE:  # disabled in CSE
        main_module_registry.register(MainModuleRoles)
        main_module_registry.register(MainModuleLDAP)
        main_module_registry.register(MainModuleSites)
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
    main_module_registry.register(MainModuleMonitoringRules)
    main_module_registry.register(MainModuleDiscoveryRules)
    main_module_registry.register(MainModuleEnforcedServices)
    main_module_registry.register(MainModuleAgentRules)
    main_module_registry.register(MainModuleOtherAgents)
    main_module_registry.register(MainModuleAgentAccessRules)
    main_module_registry.register(MainModuleSNMPRules)
    main_module_registry.register(MainModuleVMCloudContainer)
    main_module_registry.register(MainModuleOtherIntegrations)

    # Register the built-in agent download page on the top level of Setup only when the Agent Bakery
    # does not exist (e.g. when using CRE)
    if cmk_version.edition(paths.omd_root) in (cmk_version.Edition.CRE,):
        main_module_registry.register(MainModuleAgentsWindows)
        main_module_registry.register(MainModuleAgentsLinux)


class MainModuleFolder(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "folder"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("Hosts")

    @property
    def icon(self) -> Icon:
        return "folder"

    @property
    def permission(self) -> None | str:
        return "hosts"

    @property
    def description(self) -> str:
        return _("Manage monitored hosts and services and the hosts' folder structure.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleTags(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "tags"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("Tags")

    @property
    def icon(self) -> Icon:
        return "tag"

    @property
    def permission(self) -> None | str:
        # The module was renamed from hosttags to tags during 1.6 development. The permission can not
        # be changed easily for compatibility reasons. Leave old internal name for simplicity.
        return "hosttags"

    @property
    def description(self) -> str:
        return _("Tags can be used to classify hosts and services in a flexible way.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleGlobalSettings(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "globalvars"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Global settings")

    @property
    def icon(self) -> Icon:
        return "configuration"

    @property
    def permission(self) -> None | str:
        return "global"

    @property
    def description(self) -> str:
        return _(
            "Global settings for Checkmk, graphical user interface (GUI) and the monitoring core."
        )

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleReadOnly(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "read_only"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Read only mode")

    @property
    def icon(self) -> Icon:
        return "read_only"

    @property
    def permission(self) -> None | str:
        return "read_only"

    @property
    def description(self) -> str:
        return _("Set the Checkmk configuration interface to read only mode for maintenance.")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleRuleSearch(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "rule_search"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Rule search")

    @property
    def icon(self) -> Icon:
        return "search"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Search all rules and rule sets")

    @property
    def sort_index(self) -> int:
        return 5

    @property
    def is_show_more(self) -> bool:
        return False


class MainModulePredefinedConditions(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "predefined_conditions"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Predefined conditions")

    @property
    def icon(self) -> Icon:
        return "predefined_conditions"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Use predefined conditions to centralize the conditions of your rule sets.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleHostAndServiceParameters(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "host_monconf")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("Host monitoring rules")

    @property
    def icon(self) -> Icon:
        return {"icon": "folder", "emblem": "rulesets"}

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Check parameters and other configuration variables for hosts")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleHWSWInventory(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "inventory")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("HW/SW Inventory rules")

    @property
    def icon(self) -> Icon:
        return "inventory"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Manage hard- and software inventory related rule sets")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return True

    @classmethod
    def main_menu_search_terms(cls) -> Sequence[str]:
        return ["hardware", "software"]


class MainModuleNetworkingServices(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "activechecks")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("HTTP, TCP, email, ...")

    @property
    def icon(self) -> Icon:
        return "network_services"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _(
            "Configure monitoring of networking services using classical Nagios plug-ins"
            " (so called active checks)"
        )

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleOtherServices(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "custom_checks")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Other services")

    @property
    def icon(self) -> Icon:
        return "nagios"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _(
            "Integrate [active_checks#mrpe|custom nagios plug-ins] into the "
            "monitoring as active checks."
        )

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleCheckPlugins(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "check_plugins"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Catalog of check plug-ins")

    @property
    def icon(self) -> Icon:
        return "check_plugins"

    @property
    def permission(self) -> None | str:
        return "check_plugins"

    @property
    def description(self) -> str:
        return _("Browse the catalog of all check plug-ins, create static checks")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleHostGroups(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "host_groups"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("Host groups")

    @property
    def icon(self) -> Icon:
        return "hostgroups"

    @property
    def permission(self) -> None | str:
        return "groups"

    @property
    def description(self) -> str:
        return _("Organize your hosts in groups independent of the tree structure.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleHostCustomAttributes(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "host_attrs"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("Custom host attributes")

    @property
    def icon(self) -> Icon:
        return "custom_attr"

    @property
    def permission(self) -> None | str:
        return "custom_attributes"

    @property
    def description(self) -> str:
        return _("Create your own host related attributes")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleServiceGroups(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "service_groups"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Service groups")

    @property
    def icon(self) -> Icon:
        return "servicegroups"

    @property
    def permission(self) -> None | str:
        return "groups"

    @property
    def description(self) -> str:
        return _("Organize your services in groups")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleUsers(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "users"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    def title(self) -> str:
        return _("Users")

    @property
    def icon(self) -> Icon:
        return "users"

    @property
    def permission(self) -> None | str:
        return "users"

    @property
    def description(self) -> str:
        return _("Manage users of the monitoring system.")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleRoles(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "roles"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    def title(self) -> str:
        return _("Roles & permissions")

    @property
    def icon(self) -> Icon:
        return "roles"

    @property
    def permission(self) -> None | str:
        return "users"

    @property
    def description(self) -> str:
        return _("User roles are configurable sets of permissions.")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleLDAP(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "ldap_config"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    def title(self) -> str:
        return _("LDAP & Active Directory")

    @property
    def icon(self) -> Icon:
        return "ldap"

    @property
    def permission(self) -> None | str:
        return "users"

    @property
    def description(self) -> str:
        return _("Connect Checkmk with your LDAP or Active Directory to create users in Checkmk.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleUserCustomAttributes(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "user_attrs"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    def title(self) -> str:
        return _("Custom user attributes")

    @property
    def icon(self) -> Icon:
        return "custom_attr"

    @property
    def permission(self) -> None | str:
        return "custom_attributes"

    @property
    def description(self) -> str:
        return _("Create your own user related attributes")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleContactGroups(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "contact_groups"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicUsers

    @property
    def title(self) -> str:
        return _("Contact groups")

    @property
    def icon(self) -> Icon:
        return "contactgroups"

    @property
    def permission(self) -> None | str:
        return "users"

    @property
    def description(self) -> str:
        return _("Contact groups are used to assign users to hosts and services")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleNotifications(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "notifications"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    def title(self) -> str:
        return _("Notifications")

    @property
    def icon(self) -> Icon:
        return "notifications"

    @property
    def permission(self) -> None | str:
        return "notifications"

    @property
    def description(self) -> str:
        return _("Rules for the notification of contacts about host and service problems")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleAnalyzeNotifications(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "analyze_notifications"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    def title(self) -> str:
        return _("Analyze recent notifications")

    @property
    def icon(self) -> Icon:
        return "analyze"

    @property
    def permission(self) -> None | str:
        return "notifications"

    @property
    def description(self) -> str:
        return _("Analyze recent notifications with your current rule set")

    @property
    def sort_index(self) -> int:
        return 11

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleTestNotifications(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "test_notifications"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicEvents

    @property
    def title(self) -> str:
        return _("Test notifications")

    @property
    def icon(self) -> Icon:
        return "analysis"

    @property
    def permission(self) -> None | str:
        return "notifications"

    @property
    def description(self) -> str:
        return _("Test custom notifications with your current rule set")

    @property
    def sort_index(self) -> int:
        return 12

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleTimeperiods(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "timeperiods"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Time periods")

    @property
    def icon(self) -> Icon:
        return "timeperiods"

    @property
    def permission(self) -> None | str:
        return "timeperiods"

    @property
    def description(self) -> str:
        return _(
            "Time periods restrict notifications and other things to certain periods of the day."
        )

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleSites(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "sites"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Distributed monitoring")

    @property
    def icon(self) -> Icon:
        return "sites"

    @property
    def permission(self) -> None | str:
        return "sites"

    @property
    def description(self) -> str:
        return _("Distributed monitoring using multiple Checkmk sites")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return False


class MainModulePasswords(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "passwords"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Passwords")

    @property
    def icon(self) -> Icon:
        return "passwords"

    @property
    def permission(self) -> None | str:
        return "passwords"

    @property
    def description(self) -> str:
        return _("Store and share passwords for later use in checks.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleAuditLog(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "auditlog"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Audit log")

    @property
    def icon(self) -> Icon:
        return "auditlog"

    @property
    def permission(self) -> None | str:
        return "auditlog"

    @property
    def description(self) -> str:
        return _("Examine the change history of the configuration")

    @property
    def sort_index(self) -> int:
        return 80

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleAnalyzeConfig(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "analyze_config"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    def title(self) -> str:
        return _("Analyze configuration")

    @property
    def icon(self) -> Icon:
        return "analyze_config"

    @property
    def permission(self) -> None | str:
        return "analyze_config"

    @property
    def description(self) -> str:
        return _("See hints how to improve your Checkmk installation")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleCertificateOverview(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "certificate_overview"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    def title(self) -> str:
        return _("Certificate overview")

    @property
    def icon(self) -> Icon:
        return "certificate_overview"

    @property
    def permission(self) -> None | str:
        return "certificate_overview"

    @property
    def description(self) -> str:
        return _("Displays details of the certificates used by Checkmk")

    @property
    def sort_index(self) -> int:
        return 35

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleDiagnostics(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "diagnostics"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    def title(self) -> str:
        return _("Support diagnostics")

    @property
    def icon(self) -> Icon:
        loc_time = time.localtime()
        if loc_time.tm_hour == 13 and loc_time.tm_min == 37:
            return "d146n0571c5"
        return "diagnostics"

    @property
    def permission(self) -> None | str:
        return "diagnostics"

    @property
    def description(self) -> str:
        return _("Collect information of Checkmk sites for diagnostic analysis.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleMonitoringRules(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "monconf")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Service monitoring rules")

    @property
    def icon(self) -> Icon:
        return {"icon": "services", "emblem": "rulesets"}

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Service monitoring rules")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleDiscoveryRules(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "checkparams")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Discovery rules")

    @property
    def icon(self) -> Icon:
        return "service_discovery"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Discovery settings")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleEnforcedServices(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "static")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Enforced services")

    @property
    def icon(self) -> Icon:
        return "static_checks"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Configure enforced checks without using service discovery")

    @property
    def sort_index(self) -> int:
        return 25

    @property
    def is_show_more(self) -> bool:
        return True


class MainModuleAgentsWindows(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "download_agents_windows"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Windows")

    @property
    def icon(self) -> Icon:
        return "download_agents"

    @property
    def permission(self) -> None | str:
        return "download_agents"

    @property
    def description(self) -> str:
        return _("Downloads Checkmk agent and plug-ins for Windows")

    @property
    def sort_index(self) -> int:
        return 15

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentsLinux(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "download_agents_linux"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Linux")

    @property
    def icon(self) -> Icon:
        return "download_agents"

    @property
    def permission(self) -> None | str:
        return "download_agents"

    @property
    def description(self) -> str:
        return _("Downloads Checkmk agent and plug-ins for Linux")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentRules(ABCMainModule):
    @property
    def enabled(self) -> bool:
        return False

    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "agents")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Agent rules")

    @property
    def icon(self) -> Icon:
        return {"icon": "agents", "emblem": "rulesets"}

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Configuration of monitoring agents for Linux, Windows and Unix")

    @property
    def sort_index(self) -> int:
        return 80

    @property
    def is_show_more(self) -> bool:
        return True

    @classmethod
    def additional_breadcrumb_items(cls) -> Iterable[BreadcrumbItem]:
        yield BreadcrumbItem(
            title="Windows, Linux, Solaris, AIX",
            url=makeuri_contextless(
                request,
                [("mode", "agents")],
                filename="wato.py",
            ),
        )


class MainModuleOtherAgents(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "download_agents"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Other operating systems")

    @property
    def icon(self) -> Icon:
        return "os_other"

    @property
    def permission(self) -> None | str:
        return "download_agents"

    @property
    def description(self) -> str:
        return _("Downloads Checkmk agents for other operating systems")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleAgentAccessRules(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "agent")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Agent access rules")

    @property
    def icon(self) -> Icon:
        return {"icon": "agents", "emblem": "rulesets"}

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Configure agent access related settings using rule sets")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleSNMPRules(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "snmp")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("SNMP rules")

    @property
    def icon(self) -> Icon:
        return "snmp"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Configure SNMP related settings using rule sets")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleVMCloudContainer(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "vm_cloud_container")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("VM, cloud, container")

    @property
    def icon(self) -> Icon:
        return "cloud"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Integrate with VM, cloud or container platforms")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleOtherIntegrations(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "datasource_programs")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("Other integrations")

    @property
    def icon(self) -> Icon:
        return "integrations_other"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self) -> str:
        return _("Monitoring of applications such as processes, services or databases")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False
