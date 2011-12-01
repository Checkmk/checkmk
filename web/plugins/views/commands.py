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

config.declare_permission("action.reschedule",
        _("Reschedule checks"),
        _("Reschedule host and service checks"),
        [ "user", "admin" ])

multisite_commands.append({  
    "tables"      : [ "host", "service" ],
    "permission"  : "action.reschedule",
    "title"       : _("Reschedule"),
    "render"      : lambda: \
        html.button("_resched_checks", _("Reschedule active checks")),
    "action"      : lambda cmdtag, spec:
        html.var("_resched_checks") and (
            "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(time.time())),
            _("<b>reschedule an immediate check</b> of"))
})



config.declare_permission("action.notifications",
        _("Enable/disable notifications"),
        _("Enable and disable notifications on hosts and services"),
        [ "admin" ])

def command_notifications(cmdtag, spec):
    if html.var("_enable_notifications"):
        return ("ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                _("<b>enable notifications</b> for"))
    elif html.var("_disable_notifications"):
        return ("DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                _("<b>disable notifications</b> for"))

multisite_commands.append({  
    "tables"      : [ "host", "service" ],
    "permission"  : "action.notifications",
    "title"       : _("Notifications"),
    "render"      : lambda: \
       html.button("_enable_notifications", _("Enable")) == \
       html.button("_disable_notifications", _("Disable")),
    "action"      : command_notifications,
})



config.declare_permission("action.enablechecks",
        _("Enable/disable checks"),
        _("Enable and disable active or passive checks on hosts and services"),
        [ "admin" ])

def command_enable_active(cmdtag, spec):
    if html.var("_enable_checks"):
        return ("ENABLE_" + cmdtag + "_CHECKS;%s" % spec,
                _("<b>enable active checks</b> for"))
    elif html.var("_disable_checks"):
        return ("DISABLE_" + cmdtag + "_CHECKS;%s" % spec,
                _("<b>disable active checks</b> for"))

multisite_commands.append({  
    "tables"      : [ "host", "service" ],
    "permission"  : "action.enablechecks",
    "title"       : _("Active checks"),
    "render"      : lambda: \
       html.button("_enable_checks", _("Enable")) == \
       html.button("_disable_checks", _("Disable")),
    "action"      : command_enable_active,
})

def command_enable_passive(cmdtag, spec):
    if html.var("_enable_passive_checks"):
        return ("ENABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                _("<b>enable passive checks</b> for"))
    elif html.var("_disable_passive_checks"):
        return ("DISABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                _("<b>disable passive checks</b> for"))

multisite_commands.append({  
    "tables"      : [ "host", "service" ],
    "permission"  : "action.enablechecks",
    "title"       : _("Passive checks"),
    "render"      : lambda: \
       html.button("_enable_passive_checks", _("Enable")) == \
       html.button("_disable_passive_checks", _("Disable")),
    "action"      : command_enable_passive,
})



