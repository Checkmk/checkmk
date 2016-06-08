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
# defined in a plugin because they contain i18n strings.
# fields: mode, title, icon, permission, help

modules += [
      ( "folder",           _("Hosts"),     "folder", "hosts",
      _("Manage monitored hosts and services and the hosts' folder structure.")),

      ( "hosttags",         _("Host Tags"),          "hosttag", "hosttags",
      _("Tags classify hosts and are the "
        "fundament of configuration of hosts and services.")),

      ( "globalvars",        _("Global Settings"),    "configuration", "global",
      _("Global settings for Check_MK, Multisite and the monitoring core.")),

      ( "ruleeditor",        _("Host & Service Parameters"), "rulesets", "rulesets",
      _("Check parameters and other configuration variables on "
        "hosts and services") ),

      ( "static_checks",      _("Manual Checks"),     "static_checks", "rulesets",
      _("Configure fixed checks without using service discovery")),

      ( "check_plugins",     _("Check Plugins"), "check_plugins", None,
      _("Browse the catalog of all check plugins, create static checks")),

      ( "host_groups",       _("Host & Service Groups"),  "hostgroups", "groups",
      _("Organize your hosts and services in groups independent of the tree structure.") ),

      ( "users",          _("Users"),     "users", "users",
      _("Manage users of the monitoring system.") ),

      ( "roles",            _("Roles & Permissions"),     "roles", "users",
      _("User roles are configurable sets of permissions." ) ),

      ( "contact_groups",   _("Contact Groups"),     "contactgroups", "users",
      _("Contact groups are used to assign persons to hosts and services") ),

      ( "notifications",    _("Notifications"),     "notifications", "notifications",
      _("Rules for the notification of contacts about host and service problems")),

      ( "timeperiods",      _("Time Periods"),       "timeperiods", "timeperiods",
      _("Timeperiods restrict notifications and other things to certain periods of "
        "the day.") ),

      ( "pattern_editor", _("Logfile Pattern Analyzer"), "analyze", "pattern_editor",
        _("Analyze logfile pattern rules and validate logfile patterns against custom text.")),

      ( "bi_packs", _("BI - Business Intelligence"), "aggr", "bi_rules",
      _("Configuration of Check_MK's Business Intelligence component.")),

      ( "sites",  _("Distributed Monitoring"), "sites", "sites",
      _("Distributed monitoring via Multsite, distributed configuration via WATO")),

      ( "snapshot", _("Backup & Restore"), "backup", "snapshots",
        _("Make snapshots of your configuration, download, upload and restore snapshots.")),

      ( "backup", _("Backup & Restore"), "backup", "backups",
        _("Make backups of your whole site and restore previous backups.")),

      ( "icons", _("Custom Icons"), "icons", "icons",
        _("Upload your own icons that can be used in views or custom actions")),
]

# Register the builtin agent download page on the top level of WATO only when the agent bakery
# does not exist (e.g. when using CRE)
if "agents" not in modes:
    modules.append(
        ("download_agents", _("Monitoring Agents"), "download_agents", "download_agents",
         _("Downloads the Check_MK monitoring agents"))
    )
