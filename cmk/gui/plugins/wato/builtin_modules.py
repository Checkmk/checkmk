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
        return _("Global settings for Check_MK, Multisite and the monitoring core.")

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
        return "ruleeditor"

    @property
    def topic(self):
        return MainModuleTopicHosts

    @property
    def title(self):
        return _("Monitoring settings")

    @property
    def icon(self):
        return "rulesets"

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
        return _("Connect Checkmk with your LDAP or Active Directory to create users in Checmk.")

    @property
    def sort_index(self):
        return 50

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
        return _("Distributed monitoring using multiple Check_MK sites")

    @property
    def sort_index(self):
        return 80

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


class MainModuleDownloadAgents(MainModule):
    @property
    def mode_or_url(self):
        return "download_agents"

    @property
    def topic(self):
        return MainModuleTopicAgents

    @property
    def title(self):
        return _("Monitoring agents")

    @property
    def icon(self):
        return "download_agents"

    @property
    def permission(self):
        return "download_agents"

    @property
    def description(self):
        return _("Downloads the Checkmk monitoring agents")

    @property
    def sort_index(self):
        return 10

    @property
    def is_advanced(self):
        return False


# Register the builtin agent download page on the top level of WATO only when the agent bakery
# does not exist (e.g. when using CRE)
if cmk_version.is_raw_edition():
    main_module_registry.register(MainModuleDownloadAgents)
