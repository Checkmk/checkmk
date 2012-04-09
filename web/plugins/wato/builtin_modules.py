#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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
      ( "folder",           _("Hosts & folders"),     "folder", "hosts",
      _("Manage monitored hosts and services and the hosts' folder structure.")),

      ( "hosttags",         _("Host tags"),          "hosttag", "hosttags",
      _("Manage your host tags. Tags are used to classify hosts and are the "
        "fundament of the configuration of hosts and services.")),

      ( "globalvars",        _("Global settings"),    "configuration", "global",
      _("Manage global configuration settings for Check_MK, Multisite and the "

        "monitoring core here.")),
      ( "ruleeditor",        _("Host/Service configuration"), "rulesets", "rulesets",
      _("Check parameters and other variables that can be set on a per-host "
        "and per-service basis are managed via rules.") ),

      ( "host_groups",       _("Host Groups"),        "hostgroups", "groups",
      _("Organize your hosts in groups independent of the tree structure.") ),

      ( "service_groups",    _("Service Groups"),     "servicegroups", "groups",
      _("Organize services in groups for a better overview in the status display.") ),

      ( "users",          _("Users & Contacts"),     "users", "users",
      _("Manage users of Multisite and contacts of the monitoring system.") ),

      ( "roles",            _("Roles"),     "roles", "users",
      _("Manage user roles and permissions.") ),

      ( "contact_groups",   _("Contact Groups"),     "contactgroups", "users",
      _("Manage groups of contacts.") ),

      ( "timeperiods",      _("Time Periods"),       "timeperiods", "timeperiods",
      _("Timeperiods define a set of days and hours of a regular week and "
        "can be used to restrict alert notifications.") ),

      ( "sites",  _("Multisite Connections"), "sites", "sites",
      _("Configure distributed monitoring via Multsite, manage connections to remote sites.")),

      ( "auditlog", _("Audit Logfile"), "auditlog", "auditlog",
      _("The audit log keeps track of all modifications and actions of the users in WATO.")),

      ( "snapshot", _("Backup & Restore"), "backup", "snapshots",
        _("Make snapshots of your current configuration, download, upload and restore snapshots.")),
    ]

