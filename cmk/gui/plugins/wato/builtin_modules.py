#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# List of modules for main menu and WATO snapin. These modules are
# defined in a plugin because they contain cmk.gui.i18n strings.
# fields: mode, title, icon, permission, help

import time
import cmk.utils.version as cmk_version

from cmk.gui.i18n import _

from cmk.gui.plugins.wato import (
    main_module_registry,
    MainModule,
    MainModuleTopicHosts,
    MainModuleTopicServices,
    MainModuleTopicUsers,
    MainModuleTopicAgents,
    MainModuleTopicEvents,
    MainModuleTopicGeneral,
    MainModuleTopicMaintenance,
)


@main_module_registry.register
class MainModuleFolder(MainModule):
    @property
    def mode_or_url(self):
        return "folder"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Hosts")

    @property
    def icon(self):
        return "folder"

    @property
    def permission(self):
        return "hosts"

    @property
    def description(self):
        return _("Manage monitored hosts and services and the hosts' folder structure.")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleTags(MainModule):
    @property
    def mode_or_url(self):
        return "tags"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Tags")

    @property
    def icon(self):
        return "tag"

    @property
    def permission(self):
        # The module was renamed from hosttags to tags during 1.6 development. The permission can not
        # be changed easily for compatibility reasons. Leave old internal name for simplicity.
        return "hosttags"

    @property
    def description(self):
        return _("Tags can be used to classify hosts and services in a flexible way.")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleGlobalSettings(MainModule):
    @property
    def mode_or_url(self):
        return "globalvars"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Global settings")

    @property
    def icon(self):
        return "configuration"

    @property
    def permission(self):
        return "global"

    @property
    def description(self):
        return _("Global settings for Checkmk, Multisite and the monitoring core.")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleReadOnly(MainModule):
    @property
    def mode_or_url(self):
        return "read_only"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Read only mode")

    @property
    def icon(self):
        return "read_only"

    @property
    def permission(self):
        return "read_only"

    @property
    def description(self):
        return _("Set the Checkmk configuration interface to read only mode for maintenance.")

    @property
    def sort_index(self):
        return 20

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleRuleSearch(MainModule):
    @property
    def mode_or_url(self):
        return "rule_search"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Rule search")

    @property
    def icon(self):
        return "search"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Search all rules and rulesets")

    @property
    def sort_index(self):
        return 5

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModulePredefinedConditions(MainModule):
    @property
    def mode_or_url(self):
        return "predefined_conditions"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Predefined conditions")

    @property
    def icon(self):
        return "predefined_conditions"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Use predefined conditions to centralize the coniditions of your rulesets.")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleHostAndServiceParameters(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=host_monconf"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Monitoring rules")

    @property
    def icon(self):
        return "folder"

    @property
    def emblem(self):
        return "settings"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Check parameters and other configuration variables on hosts and services")

    @property
    def sort_index(self):
        return 20

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleHWSWInventory(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=inventory"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("HW/SW inventory rules")

    @property
    def icon(self):
        return "inventory"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Manage Hard- and software inventory related rulesets")

    @property
    def sort_index(self):
        return 60

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleNetworkingServices(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=activechecks"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Check networking services")

    @property
    def icon(self):
        return "network_services"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Configure monitoring of networking services using classical nagios plugins"
                 " (so called active checks)")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleIntegrateNagiosPlugins(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=custom_checks"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Integrate Nagios plugins")

    @property
    def icon(self):
        return "nagios"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Integrate [cms_active_checks#mrpe|custom nagios plugins] into the "
                 "monitoring as active checks.")

    @property
    def sort_index(self):
        return 40

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleStaticChecks(MainModule):
    @property
    def mode_or_url(self):
        return "static_checks"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Manual services")

    @property
    def icon(self):
        return "static_checks"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Configure fixed checks without using service discovery")

    @property
    def sort_index(self):
        return 50

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleCheckPlugins(MainModule):
    @property
    def mode_or_url(self):
        return "check_plugins"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Catalog of check plugins")

    @property
    def icon(self):
        return "check_plugins"

    @property
    def permission(self):
        return None

    @property
    def description(self):
        return _("Browse the catalog of all check plugins, create static checks")

    @property
    def sort_index(self):
        return 70

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleHostGroups(MainModule):
    @property
    def mode_or_url(self):
        return "host_groups"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Groups")

    @property
    def icon(self):
        return "hostgroups"

    @property
    def permission(self):
        return "groups"

    @property
    def description(self):
        return _("Organize your hosts in groups independent of the tree structure.")

    @property
    def sort_index(self):
        return 50

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleHostCustomAttributes(MainModule):
    @property
    def mode_or_url(self):
        return "host_attrs"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Custom attributes")

    @property
    def icon(self):
        return "custom_attr"

    @property
    def permission(self):
        return "custom_attributes"

    @property
    def description(self):
        return _("Create your own host related attributes")

    @property
    def sort_index(self):
        return 55

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleServiceGroups(MainModule):
    @property
    def mode_or_url(self):
        return "service_groups"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Groups")

    @property
    def icon(self):
        return "servicegroups"

    @property
    def permission(self):
        return "groups"

    @property
    def description(self):
        return _("Organize your services in groups")

    @property
    def sort_index(self):
        return 60

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleUsers(MainModule):
    @property
    def mode_or_url(self):
        return "users"

    @property
    def topic(self):
        return MainModuleTopicUsers

    @property
    def title(self):
        return _("Users")

    @property
    def icon(self):
        return "users"

    @property
    def permission(self):
        return "users"

    @property
    def description(self):
        return _("Manage users of the monitoring system.")

    @property
    def sort_index(self):
        return 20

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleRoles(MainModule):
    @property
    def mode_or_url(self):
        return "roles"

    @property
    def topic(self):
        return MainModuleTopicUsers

    @property
    def title(self):
        return _("Roles & permissions")

    @property
    def icon(self):
        return "roles"

    @property
    def permission(self):
        return "users"

    @property
    def description(self):
        return _("User roles are configurable sets of permissions.")

    @property
    def sort_index(self):
        return 40

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleLDAP(MainModule):
    @property
    def mode_or_url(self):
        return "ldap_config"

    @property
    def topic(self):
        return MainModuleTopicUsers

    @property
    def title(self):
        return _("LDAP & Active Directory")

    @property
    def icon(self):
        return "roles"

    @property
    def permission(self):
        return "users"

    @property
    def description(self):
        return _("Connect Checkmk with your LDAP or Active Directory to create users in Checkmk.")

    @property
    def sort_index(self):
        return 50

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleUserCustomAttributes(MainModule):
    @property
    def mode_or_url(self):
        return "user_attrs"

    @property
    def topic(self):
        return MainModuleTopicUsers

    @property
    def title(self):
        return _("Custom attributes")

    @property
    def icon(self):
        return "custom_attr"

    @property
    def permission(self):
        return "custom_attributes"

    @property
    def description(self):
        return _("Create your own user related attributes")

    @property
    def sort_index(self):
        return 55

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleContactGroups(MainModule):
    @property
    def mode_or_url(self):
        return "contact_groups"

    @property
    def topic(self):
        return MainModuleTopicUsers

    @property
    def title(self):
        return _("Groups")

    @property
    def icon(self):
        return "contactgroups"

    @property
    def permission(self):
        return "users"

    @property
    def description(self):
        return _("Contact groups are used to assign users to hosts and services")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleNotifications(MainModule):
    @property
    def mode_or_url(self):
        return "notifications"

    @property
    def topic(self):
        return MainModuleTopicEvents

    @property
    def title(self):
        return _("Notifications")

    @property
    def icon(self):
        return "notifications"

    @property
    def permission(self):
        return "notifications"

    @property
    def description(self):
        return _("Rules for the notification of contacts about host and service problems")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleTimeperiods(MainModule):
    @property
    def mode_or_url(self):
        return "timeperiods"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Time periods")

    @property
    def icon(self):
        return "timeperiods"

    @property
    def permission(self):
        return "timeperiods"

    @property
    def description(self):
        return _(
            "Timeperiods restrict notifications and other things to certain periods of the day.")

    @property
    def sort_index(self):
        return 40

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleSites(MainModule):
    @property
    def mode_or_url(self):
        return "sites"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Distributed monitoring")

    @property
    def icon(self):
        return "sites"

    @property
    def permission(self):
        return "sites"

    @property
    def description(self):
        return _("Distributed monitoring using multiple Checkmk sites")

    @property
    def sort_index(self):
        return 70

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleBackup(MainModule):
    @property
    def mode_or_url(self):
        return "backup"

    @property
    def topic(self):
        return MainModuleTopicMaintenance

    @property
    def title(self):
        return _("Backups")

    @property
    def icon(self):
        return "backup"

    @property
    def permission(self):
        return "backups"

    @property
    def description(self):
        return _("Make backups of your whole site and restore previous backups.")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModulePasswords(MainModule):
    @property
    def mode_or_url(self):
        return "passwords"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Passwords")

    @property
    def icon(self):
        return "passwords"

    @property
    def permission(self):
        return "passwords"

    @property
    def description(self):
        return _("Store and share passwords for later use in checks.")

    @property
    def sort_index(self):
        return 50

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleAuditLog(MainModule):
    @property
    def mode_or_url(self):
        return "auditlog"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Audit log")

    @property
    def icon(self):
        return "auditlog"

    @property
    def permission(self):
        return "auditlog"

    @property
    def description(self):
        return _("Examine the change history of the configuration")

    @property
    def sort_index(self):
        return 80

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleIcons(MainModule):
    @property
    def mode_or_url(self):
        return "icons"

    @property
    def topic(self):
        return MainModuleTopicGeneral

    @property
    def title(self):
        return _("Custom icons")

    @property
    def icon(self):
        return "icons"

    @property
    def permission(self):
        return "icons"

    @property
    def description(self):
        return _("Extend the Checkmk GUI with your custom icons")

    @property
    def sort_index(self):
        return 85

    @property
    def is_advanced(self):
        return True


@main_module_registry.register
class MainModuleAnalyzeConfig(MainModule):
    @property
    def mode_or_url(self):
        return "analyze_config"

    @property
    def topic(self):
        return MainModuleTopicMaintenance

    @property
    def title(self):
        return _("Analyze configuration")

    @property
    def icon(self):
        return "analyze_config"

    @property
    def permission(self):
        return "analyze_config"

    @property
    def description(self):
        return _("See hints how to improve your Checkmk installation")

    @property
    def sort_index(self):
        return 40

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleReleaseNotes(MainModule):
    @property
    def mode_or_url(self):
        return "version.py"

    @property
    def topic(self):
        return MainModuleTopicMaintenance

    @property
    def title(self):
        return _("Release notes")

    @property
    def icon(self):
        return "release_notes"

    @property
    def permission(self):
        return None

    @property
    def description(self):
        return _("Learn something about what changed at Checkmk.")

    @property
    def sort_index(self):
        return 60

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleDiagnostics(MainModule):
    @property
    def mode_or_url(self):
        return "diagnostics"

    @property
    def topic(self):
        return MainModuleTopicMaintenance

    @property
    def title(self):
        return _("Support diagnostics")

    @property
    def icon(self):
        loc_time = time.localtime()
        if loc_time.tm_hour == 13 and loc_time.tm_min == 37:
            return "d146n0571c5"
        return "diagnostics"

    @property
    def permission(self):
        return "diagnostics"

    @property
    def description(self):
        return _("Collect information of Checkmk sites for diagnostic analysis.")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleMonitoringRules(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=monconf"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Monitoring rules")

    @property
    def icon(self):
        return "services"

    @property
    def emblem(self):
        return "settings"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Monitoring rules")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleDiscoveryRules(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=checkparams"

    @property
    def topic(self):
        return MainModuleTopicServices

    @property
    def title(self):
        return _("Discovery rules")

    @property
    def icon(self):
        return "service_discovery"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Discovery settings")

    @property
    def sort_index(self):
        return 20

    @property
    def is_advanced(self):
        return False


class MainModuleAgentsWindows(MainModule):
    @property
    def mode_or_url(self):
        return "download_agents_windows"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Windows")

    @property
    def icon(self):
        return "download_agents_windows"

    @property
    def permission(self):
        return "download_agents"

    @property
    def description(self):
        return _("Downloads Checkmk agent and plugins for Windows")

    @property
    def sort_index(self):
        return 15

    @property
    def is_advanced(self):
        return False


class MainModuleAgentsLinux(MainModule):
    @property
    def mode_or_url(self):
        return "download_agents_linux"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Linux")

    @property
    def icon(self):
        return "download_agents_linux"

    @property
    def permission(self):
        return "download_agents"

    @property
    def description(self):
        return _("Downloads Checkmk agent and plugins for Linux")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


# Register the builtin agent download page on the top level of WATO only when the agent bakery
# does not exist (e.g. when using CRE)
if cmk_version.is_raw_edition():
    main_module_registry.register(MainModuleAgentsWindows)
    main_module_registry.register(MainModuleAgentsLinux)


@main_module_registry.register
class MainModuleOtherAgents(MainModule):
    @property
    def mode_or_url(self):
        return "download_agents"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Other operating systems")

    @property
    def icon(self):
        return "os_other"

    @property
    def permission(self):
        return "download_agents"

    @property
    def description(self):
        return _("Downloads Checkmk agents for other operating systems")

    @property
    def sort_index(self):
        return 20

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleAgentAccessRules(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=agent"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Agent access rules")

    @property
    def icon(self):
        return "agents"

    @property
    def emblem(self):
        return "settings"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Configure agent access related settings using rulesets")

    @property
    def sort_index(self):
        return 60

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleSNMPRules(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=snmp"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("SNMP rules")

    @property
    def icon(self):
        return "snmp"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Configure SNMP related settings using rulesets")

    @property
    def sort_index(self):
        return 70

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleVMCloudContainer(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=vm_cloud_container"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("VM, Cloud, Container")

    @property
    def icon(self):
        return "cloud"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Integrate with VM, cloud or container platforms")

    @property
    def sort_index(self):
        return 30

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleOtherIntegrations(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=datasource_programs"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Other integrations")

    @property
    def icon(self):
        return "integrations_other"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")

    @property
    def sort_index(self):
        return 40

    @property
    def is_advanced(self):
        return False


@main_module_registry.register
class MainModuleCustomIntegrations(MainModule):
    @property
    def mode_or_url(self):
        return "wato.py?mode=rulesets&group=custom_integrations"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Custom integrations")

    @property
    def icon(self):
        return "integrations_custom"

    @property
    def permission(self):
        return "rulesets"

    @property
    def description(self):
        return _("Integrate custom platform connections (special agents)")

    @property
    def sort_index(self):
        return 50

    @property
    def is_advanced(self):
        return True
