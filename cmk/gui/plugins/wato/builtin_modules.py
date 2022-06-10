#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# List of modules for main menu and WATO snapin. These modules are
# defined in a plugin because they contain cmk.gui.i18n strings.
# fields: mode, title, icon, permission, help

import time
from typing import Iterable

import cmk.utils.version as cmk_version

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ABCMainModule,
    main_module_registry,
    MainModuleTopicAgents,
    MainModuleTopicEvents,
    MainModuleTopicGeneral,
    MainModuleTopicHosts,
    MainModuleTopicMaintenance,
    MainModuleTopicServices,
    MainModuleTopicUsers,
)
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopic
from cmk.gui.type_defs import Icon
from cmk.gui.utils.urls import makeuri_contextless, makeuri_contextless_rulespec_group


@main_module_registry.register
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
    def description(self):
        return _("Manage monitored hosts and services and the hosts' folder structure.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Tags can be used to classify hosts and services in a flexible way.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Global settings for Checkmk, Multisite and the monitoring core.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Set the Checkmk configuration interface to read only mode for maintenance.")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Search all rules and rulesets")

    @property
    def sort_index(self) -> int:
        return 5

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Use predefined conditions to centralize the coniditions of your rulesets.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Check parameters and other configuration variables for hosts")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
class MainModuleHWSWInventory(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "inventory")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicHosts

    @property
    def title(self) -> str:
        return _("HW/SW inventory rules")

    @property
    def icon(self) -> Icon:
        return "inventory"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self):
        return _("Manage Hard- and software inventory related rulesets")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
class MainModuleNetworkingServices(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "activechecks")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("HTTP, TCP, Email, ...")

    @property
    def icon(self) -> Icon:
        return "network_services"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self):
        return _(
            "Configure monitoring of networking services using classical nagios plugins"
            " (so called active checks)"
        )

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
class MainModuleOtherServices(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "custom_checks")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Other Services")

    @property
    def icon(self) -> Icon:
        return "nagios"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self):
        return _(
            "Integrate [active_checks#mrpe|custom nagios plugins] into the "
            "monitoring as active checks."
        )

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
class MainModuleCheckPlugins(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "check_plugins"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicServices

    @property
    def title(self) -> str:
        return _("Catalog of check plugins")

    @property
    def icon(self) -> Icon:
        return "check_plugins"

    @property
    def permission(self) -> None | str:
        return "check_plugins"

    @property
    def description(self):
        return _("Browse the catalog of all check plugins, create static checks")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Organize your hosts in groups independent of the tree structure.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Create your own host related attributes")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Organize your services in groups")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Manage users of the monitoring system.")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("User roles are configurable sets of permissions.")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Connect Checkmk with your LDAP or Active Directory to create users in Checkmk.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Create your own user related attributes")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("Contact groups are used to assign users to hosts and services")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Rules for the notification of contacts about host and service problems")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _(
            "Timeperiods restrict notifications and other things to certain periods of the day."
        )

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Distributed monitoring using multiple Checkmk sites")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
class MainModuleBackup(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "backup"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    def title(self) -> str:
        return _("Backups")

    @property
    def icon(self) -> Icon:
        return "backup"

    @property
    def permission(self) -> None | str:
        return "backups"

    @property
    def description(self):
        return _("Make backups of your whole site and restore previous backups.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Store and share passwords for later use in checks.")

    @property
    def sort_index(self) -> int:
        return 50

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Examine the change history of the configuration")

    @property
    def sort_index(self) -> int:
        return 80

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
class MainModuleIcons(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "icons"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Custom icons")

    @property
    def icon(self) -> Icon:
        return "icons"

    @property
    def permission(self) -> None | str:
        return "icons"

    @property
    def description(self):
        return _("Extend the Checkmk GUI with your custom icons")

    @property
    def sort_index(self) -> int:
        return 85

    @property
    def is_show_more(self) -> bool:
        return True


@main_module_registry.register
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
    def description(self):
        return _("See hints how to improve your Checkmk installation")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Collect information of Checkmk sites for diagnostic analysis.")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Service monitoring rules")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Discovery settings")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
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
    def description(self):
        return _("Downloads Checkmk agent and plugins for Windows")

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
    def description(self):
        return _("Downloads Checkmk agent and plugins for Linux")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False


# Register the builtin agent download page on the top level of WATO only when the agent bakery
# does not exist (e.g. when using CRE)
if cmk_version.is_raw_edition():
    main_module_registry.register(MainModuleAgentsWindows)
    main_module_registry.register(MainModuleAgentsLinux)


@main_module_registry.register
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
    def description(self):
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


@main_module_registry.register
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
    def description(self):
        return _("Downloads Checkmk agents for other operating systems")

    @property
    def sort_index(self) -> int:
        return 20

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Configure agent access related settings using rulesets")

    @property
    def sort_index(self) -> int:
        return 60

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Configure SNMP related settings using rulesets")

    @property
    def sort_index(self) -> int:
        return 70

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
class MainModuleVMCloudContainer(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless_rulespec_group(request, "vm_cloud_container")

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicAgents

    @property
    def title(self) -> str:
        return _("VM, Cloud, Container")

    @property
    def icon(self) -> Icon:
        return "cloud"

    @property
    def permission(self) -> None | str:
        return "rulesets"

    @property
    def description(self):
        return _("Integrate with VM, cloud or container platforms")

    @property
    def sort_index(self) -> int:
        return 30

    @property
    def is_show_more(self) -> bool:
        return False


@main_module_registry.register
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
    def description(self):
        return _("Monitoring of applications such as processes, services or databases")

    @property
    def sort_index(self) -> int:
        return 40

    @property
    def is_show_more(self) -> bool:
        return False
