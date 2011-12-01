#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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


# Declarations of commands on monitoring objects. This file is
# read in with execfile by views.py.
#
# Each command has the following aspects:
#
# - permission
# - title
# - table ("hostservices", "downtime", "comment")
# - function that outputs the HTML input fields
# - function that creates the nagios command and title

# config.declare_permission("action.notifications",
#         _("Enable/disable notifications"),
#         _("Enable and disable notifications on hosts and services"),
#         [ "admin" ])
# 
# multisite_commands.append({  
#     "tables"      : [ "host", "service" ],
#     "permission"  : "action.notifications",
#     "title"       : _("Notifications"),
#     "render"      : lambda: \
#        html.button("_enable_notifications", _("Enable")) == \
#        html.button("_disable_notifications", _("Disable")),
#     "action"      : lambda cmdtag, spec: \
#        "ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
#        _("<b>enable notifications</b> for")
# })
