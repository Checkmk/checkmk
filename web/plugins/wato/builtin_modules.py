#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# List of modules for main menu and WATO snapin. These modules are
# defined in a plugin because they contain i18n strings.
# fields: mode, title, icon, permission, help

modules = [
      ( "folder",           _("Hosts & Folders"),     "folder", "hosts",
      _("Manage monitored hosts and services and the hosts' folder structure.")),

      ( "hosttags",         _("Host Tags"),          "hosttag", "hosttags",
      _("Tags classify hosts and are the "
        "fundament of configuration of hosts and services.")),

      ( "globalvars",        _("Global Settings"),    "configuration", "global",
      _("Global settings for Check_MK, Multisite and the monitoring core.")),

      ( "ruleeditor",        _("Host &amp; Service Parameters"), "rulesets", "rulesets",
      _("Check parameters and other configuration variables on "
        "hosts and services") ),

      ( "host_groups",       _("Host Groups"),        "hostgroups", "groups",
      _("Organize your hosts in groups independent of the tree structure.") ),

      ( "service_groups",    _("Service Groups"),     "servicegroups", "groups",
      _("Organize services in groups for a better overview in the status display.") ),

      ( "users",          _("Users & Contacts"),     "users", "users",
      _("Manage users of Multisite and contacts of the monitoring system.") ),

      ( "roles",            _("Roles & Permissions"),     "roles", "users",
      _("User roles are configurable sets of permissions." ) ),

      ( "contact_groups",   _("Contact Groups"),     "contactgroups", "users",
      _("Contact groups are used to assign persons to hosts and services") ),

      ( "timeperiods",      _("Time Periods"),       "timeperiods", "timeperiods",
      _("Timeperiods restrict notifications and other things to certain periods of "
        "the day.") ),

      ( "sites",  _("Distributed Monitoring"), "sites", "sites",
      _("Distributed monitoring via Multsite, distributed configuration via WATO")),

      ( "auditlog", _("Audit Logfile"), "auditlog", "auditlog",
      _("Keep track of all modifications and actions of the users in WATO.")),

      ( "snapshot", _("Backup & Restore"), "backup", "snapshots",
        _("Make snapshots of your configuration, download, upload and restore snapshots.")),

      ( "pattern_editor", _("Logfile Pattern Analyzer"), "analyze", "pattern_editor",
        _("Analyze logfile pattern rules and validate logfile patterns against custom text.")),
    ]

