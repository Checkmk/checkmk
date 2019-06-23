#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# List of modules for main menu and WATO snapin. These modules are
# defined in a plugin because they contain cmk.gui.i18n strings.
# fields: mode, title, icon, permission, help

import cmk

from cmk.gui.i18n import _

from cmk.gui.plugins.wato import (
    main_module_registry,
    MainModule,
)


@main_module_registry.register
class MainModuleFolder(MainModule):
    @property
    def mode_or_url(self):
        return "folder"

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


@main_module_registry.register
class MainModuleTags(MainModule):
    @property
    def mode_or_url(self):
        return "tags"

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
        return 15


@main_module_registry.register
class MainModuleGlobalSettings(MainModule):
    @property
    def mode_or_url(self):
        return "globalvars"

    @property
    def title(self):
        return _("Global Settings")

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
        return 20


@main_module_registry.register
class MainModuleHostAndServiceParameters(MainModule):
    @property
    def mode_or_url(self):
        return "ruleeditor"

    @property
    def title(self):
        return _("Host & Service Parameters")

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
        return 25


@main_module_registry.register
class MainModuleStaticChecks(MainModule):
    @property
    def mode_or_url(self):
        return "static_checks"

    @property
    def title(self):
        return _("Manual Checks")

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
        return 30


@main_module_registry.register
class MainModuleCheckPlugins(MainModule):
    @property
    def mode_or_url(self):
        return "check_plugins"

    @property
    def title(self):
        return _("Check Plugins")

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
        return 35


@main_module_registry.register
class MainModuleHostAndServiceGroups(MainModule):
    @property
    def mode_or_url(self):
        return "host_groups"

    @property
    def title(self):
        return _("Host & Service Groups")

    @property
    def icon(self):
        return "hostgroups"

    @property
    def permission(self):
        return "groups"

    @property
    def description(self):
        return _("Organize your hosts and services in groups independent of the tree structure.")

    @property
    def sort_index(self):
        return 40


@main_module_registry.register
class MainModuleUsers(MainModule):
    @property
    def mode_or_url(self):
        return "users"

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
        return 45


@main_module_registry.register
class MainModuleRoles(MainModule):
    @property
    def mode_or_url(self):
        return "roles"

    @property
    def title(self):
        return _("Roles & Permissions")

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
        return 50


@main_module_registry.register
class MainModuleContactGroups(MainModule):
    @property
    def mode_or_url(self):
        return "contact_groups"

    @property
    def title(self):
        return _("Contact Groups")

    @property
    def icon(self):
        return "contactgroups"

    @property
    def permission(self):
        return "users"

    @property
    def description(self):
        return _("Contact groups are used to assign persons to hosts and services")

    @property
    def sort_index(self):
        return 55


@main_module_registry.register
class MainModuleNotifications(MainModule):
    @property
    def mode_or_url(self):
        return "notifications"

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
        return 60


@main_module_registry.register
class MainModuleTimeperiods(MainModule):
    @property
    def mode_or_url(self):
        return "timeperiods"

    @property
    def title(self):
        return _("Time Periods")

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
        return 65


@main_module_registry.register
class MainModuleSites(MainModule):
    @property
    def mode_or_url(self):
        return "sites"

    @property
    def title(self):
        return _("Distributed Monitoring")

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
        return 75


@main_module_registry.register
class MainModuleBackup(MainModule):
    @property
    def mode_or_url(self):
        return "backup"

    @property
    def title(self):
        return _("Backup")

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
        return 80


@main_module_registry.register
class MainModulePasswords(MainModule):
    @property
    def mode_or_url(self):
        return "passwords"

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
        return 85


@main_module_registry.register
class MainModuleAnalyzeConfig(MainModule):
    @property
    def mode_or_url(self):
        return "analyze_config"

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
        return _("See hints how to improve your Check_MK installation")

    @property
    def sort_index(self):
        return 90


@main_module_registry.register
class MainModulePatternEditor(MainModule):
    @property
    def mode_or_url(self):
        return "pattern_editor"

    @property
    def title(self):
        return _("Logfile Pattern Analyzer")

    @property
    def icon(self):
        return "analyze"

    @property
    def permission(self):
        return "pattern_editor"

    @property
    def description(self):
        return _("Analyze logfile pattern rules and validate logfile patterns against custom text.")

    @property
    def sort_index(self):
        return 95


@main_module_registry.register
class MainModuleIcons(MainModule):
    @property
    def mode_or_url(self):
        return "icons"

    @property
    def title(self):
        return _("Custom Icons")

    @property
    def icon(self):
        return "icons"

    @property
    def permission(self):
        return "icons"

    @property
    def description(self):
        return _("Upload your own icons that can be used in views or custom actions")

    @property
    def sort_index(self):
        return 100


class MainModuleDownloadAgents(MainModule):
    @property
    def mode_or_url(self):
        return "download_agents"

    @property
    def title(self):
        return _("Monitoring Agents")

    @property
    def icon(self):
        return "download_agents"

    @property
    def permission(self):
        return "download_agents"

    @property
    def description(self):
        return _("Downloads the Check_MK monitoring agents")

    @property
    def sort_index(self):
        return 5


# Register the builtin agent download page on the top level of WATO only when the agent bakery
# does not exist (e.g. when using CRE)
if cmk.is_raw_edition():
    main_module_registry.register(MainModuleDownloadAgents)
