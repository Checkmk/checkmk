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

#import datetime, traceback
#file('/tmp/1', 'a').write('%s %s\n%s' % (datetime.datetime.now(), current_language, ''.join(traceback.format_stack())))

# RESCHEDULE ACTIVE CHECKS
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
    "action"      : lambda cmdtag, spec, row:
        html.var("_resched_checks") and (
            "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(time.time())),
            _("<b>reschedule an immediate check</b> of"))
})


# ENABLE/DISABLE NOTIFICATIONS
config.declare_permission("action.notifications",
        _("Enable/disable notifications"),
        _("Enable and disable notifications on hosts and services"),
        [ "admin" ])

def command_notifications(cmdtag, spec, row):
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


# ENABLE/DISABLE ACTIVE CHECKS
config.declare_permission("action.enablechecks",
        _("Enable/disable checks"),
        _("Enable and disable active or passive checks on hosts and services"),
        [ "admin" ])

def command_enable_active(cmdtag, spec, row):
    if html.var("_enable_checks"):
        return ("ENABLE_" + cmdtag + "_CHECK;%s" % spec,
                _("<b>enable active checks</b> for"))
    elif html.var("_disable_checks"):
        return ("DISABLE_" + cmdtag + "_CHECK;%s" % spec,
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


# ENABLE/DISABLE PASSIVE CHECKS
def command_enable_passive(cmdtag, spec, row):
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



# CLEAR MODIFIED ATTRIBUTES
config.declare_permission("action.clearmodattr",
        _("Clear modified attributes"),
        _("Remove the information that an attribute (like check enabling) has been changed"),
        [ "admin" ])

multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.clearmodattr",
    "title"       : _("Modified attributes"),
    "render"      : lambda: \
       html.button("_clear_modattr", _('Clear information about modified attributes')),
    "action"      : lambda cmdtag, spec, row: (
        html.var("_clear_modattr") and (
        "CHANGE_" + cmdtag + "_MODATTR;%s;0" % spec,
         _("<b>clear the information about modified attributes</b> of"))),
})

# FAKE CHECKS
config.declare_permission("action.fakechecks",
        _("Fake check results"),
        _("Manually submit check results for host and service checks"),
        [ "admin" ])

def command_fake_checks(cmdtag, spec, row):
    for s in [0,1,2,3]:
        statename = html.var("_fake_%d" % s)
        if statename:
            pluginoutput = _("Manually set to %s by %s") % (statename, config.user_id)
            if cmdtag == "SVC":
                cmdtag = "SERVICE"
            command = "PROCESS_%s_CHECK_RESULT;%s;%s;%s" % (cmdtag, spec, s, pluginoutput)
            title = _("<b>manually set check results to %s</b> for") % statename
            return command, title


multisite_commands.append({
    "tables"      : [ "host" ],
    "permission"  : "action.fakechecks",
    "title"       : _("Fake check results"),
    "render"      : lambda: \
       html.button("_fake_0", _("Up")) == \
       html.button("_fake_1", _("Down")) == \
       html.button("_fake_2", _("Unreachable")),
    "action"      : command_fake_checks,
})

multisite_commands.append({
    "tables"      : [ "service" ],
    "permission"  : "action.fakechecks",
    "title"       : _("Fake check results"),
    "render"      : lambda: \
       html.button("_fake_0", _("OK")) == \
       html.button("_fake_1", _("Warning")) == \
       html.button("_fake_2", _("Critical")) == \
       html.button("_fake_3", _("Unknown")),
    "action"      : command_fake_checks,
})

# SEND CUSTOM NOTIFICATION
config.declare_permission("action.customnotification",
        _("Send custom notification"),
        _("Manually let the core send a notification to a host or service in order "
          "to test if notifications are setup correctly"),
        [ "user", "admin" ])

def command_custom_notification(cmdtag, spec, row):
    if html.var("_customnotification"):
        comment = html.var_utf8("_cusnot_comment")
        broadcast = html.get_checkbox("_cusnot_broadcast") and 1 or 0
        forced = html.get_checkbox("_cusnot_forced") and 2 or 0
        command = "SEND_CUSTOM_%s_NOTIFICATION;%s;%s;%s;%s" % \
                ( cmdtag, spec, broadcast + forced, config.user_id, comment)
        title = _("<b>send a custom notification</b> regarding")
        return command, title


multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.customnotification",
    "title"       : _("Custom notification"),
    "render"      : lambda: \
        html.write(_('Comment') + ": ") == \
        html.text_input("_cusnot_comment", "TEST", size=20, submit="_customnotification") == \
        html.write(" &nbsp; ") == \
        html.checkbox("_cusnot_forced", False, label=_("forced")) == \
        html.checkbox("_cusnot_broadcast", False, label=_("broadcast")) == \
        html.write(" &nbsp; ") == \
        html.button("_customnotification", _('Send')),
    "action"      : command_custom_notification,
})

# ACKNOWLEDGE
config.declare_permission("action.acknowledge",
        _("Acknowledge"),
        _("Acknowledge host and service problems and remove acknowledgements"),
        [ "user", "admin" ])

def command_acknowledgement(cmdtag, spec, row):
    if html.var("_acknowledge"):
        comment = html.var_utf8("_ack_comment")
        if not comment:
            raise MKUserError("_ack_comment", _("You need to supply a comment."))
        sticky = html.var("_ack_sticky") and 2 or 0
        sendnot = html.var("_ack_notify") and 1 or 0
        perscomm = html.var("_ack_persistent") and 1 or 0
        command = "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;%d;%d;%d;%s" % \
                      (spec, sticky, sendnot, perscomm, config.user_id) + (";%s" % comment)
        title = _("<b>acknowledge the problems</b> of")
        return command, title

    elif html.var("_remove_ack"):
        command = "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec
        title = _("<b>remove acknowledgements</b> from")
        return command, title


multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.acknowledge",
    "title"       : _("Acknowledge"),
    "render"      : lambda: \
        html.button("_acknowledge", _("Acknowledge")) == \
        html.button("_remove_ack", _("Remove Acknowledge")) == \
        html.write("<hr>") == \
        html.checkbox("_ack_sticky", True, label=_("sticky")) == \
        html.checkbox("_ack_notify", True, label=_("send notification")) == \
        html.checkbox("_ack_persistent", False, label=_('persistent comment')) == \
        html.write("<hr>") == \
        html.write(_("Comment") + ": ") == \
        html.text_input("_ack_comment", size=48, submit="_acknowledge"),
    "action"      : command_acknowledgement,
    "group"       : _("Acknowledge"),
})


# COMMENTS
config.declare_permission("action.addcomment",
        _("Add comments"),
        _("Add comments to hosts or services, and remove comments"),
        [ "user", "admin" ])

def command_comment(cmdtag, spec, row):
    if html.var("_add_comment"):
        comment = html.var_utf8("_comment")
        if not comment:
            raise MKUserError("_comment", _("You need to supply a comment."))
        command = "ADD_" + cmdtag + "_COMMENT;%s;1;%s" % \
                  (spec, config.user_id) + (";%s" % comment)
        title = _("<b>add a comment to</b>")
        return command, title

multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.addcomment",
    "title"       : _("Add comment"),
    "render"      : lambda: \
        html.write(_('Comment')+": ") == \
        html.text_input("_comment", size=33, submit="_add_comment") == \
        html.write(" &nbsp; ") == \
        html.button("_add_comment", _("Add comment")),
    "action"      : command_comment,
})

# DOWNTIMES
config.declare_permission("action.downtimes",
        _("Set/Remove Downtimes"),
        _("Schedule and remove downtimes on hosts and services"),
        [ "user", "admin" ])

def command_downtime(cmdtag, spec, row):
    down_from = int(time.time())
    down_to = None

    if html.var("_down_2h"):
        down_to = down_from + 7200
        title = _("<b>schedule an immediate 2-hour downtime</b> on")

    elif html.var("_down_today"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = _("<b>schedule an immediate downtime until 24:00:00</b> on")

    elif html.var("_down_week"):
        br = time.localtime(down_from)
        wday = br.tm_wday
        days_plus = 6 - wday
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        down_to += days_plus * 24 * 3600
        title = _("<b>schedule an immediate downtime until sunday night</b> on")

    elif html.var("_down_month"):
        br = time.localtime(down_from)
        new_month = br.tm_mon + 1
        if new_month == 13:
            new_year = br.tm_year + 1
            new_month = 1
        else:
            new_year = br.tm_year
        down_to = time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, br.tm_isdst))
        title = _("<b>schedule an immediate downtime until end of month</b> on")

    elif html.var("_down_year"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, 12, 31, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = _("<b>schedule an immediate downtime until end of %d</b> on") % br.tm_year

    elif html.var("_down_from_now"):
        try:
            minutes = int(html.var("_down_minutes"))
        except:
            minutes = 0

        if minutes <= 0:
            raise MKUserError("_down_minutes", _("Please enter a positive number of minutes."))

        down_to = time.time() + minutes * 60
        title = _("<b>schedule an immediate downtime for the next %d minutes</b> on" % minutes)

    elif html.var("_down_custom"):
        down_from = html.get_datetime_input("_down_from")
        down_to   = html.get_datetime_input("_down_to")
        if down_to < time.time():
            raise MKUserError("_down_to", _("You cannot set a downtime that ends in the past. "
                         "This incident will be reported."))

        title = _("<b>schedule a downtime from %s to %s</b> on ") % (
            time.asctime(time.localtime(down_from)),
            time.asctime(time.localtime(down_to)))

    elif html.var("_down_remove"):
        downtime_ids = []
        if cmdtag == "HOST":
            prefix = "host_"
        else:
            prefix = "service_"
        for id in row[prefix + "downtimes"]:
            if id != "":
                downtime_ids.append(int(id))

        commands = []
        for dtid in downtime_ids:
            commands.append("DEL_%s_DOWNTIME;%d\n" % (cmdtag, dtid))
        title = _("<b>remove all scheduled downtimes</b> of ")
        return commands, title

    if down_to:
        comment = html.var_utf8("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        if html.var("_down_flexible"):
            fixed = 0
            duration = html.get_time_input("_down_duration", _("the duration"))
        else:
            fixed = 1
            duration = 0

        if html.var("_include_childs"): # only for hosts
            specs = [ spec ] + get_child_hosts(row["site"], [spec], recurse = not not html.var("_include_childs_recurse"))
        else:
            specs = [ spec ]

        commands = [(("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % spec ) \
                   + ("%d;%d;%d;0;%d;%s;" % (down_from, down_to, fixed, duration, config.user_id)) \
                   + comment) for spec in specs]
        return commands, title

def get_child_hosts(site, hosts, recurse):
    hosts = set(hosts)
    html.live.set_only_sites([site])
    query = "GET hosts\nColumns: name\n"
    for h in hosts:
        query += "Filter: parents >= %s\n" % h
    query += "Or: %d\n" % len(hosts)
    childs = html.live.query_column(query)
    html.live.set_only_sites(None)
    # Recursion, but try to avoid duplicate work
    childs = set(childs)
    new_childs = childs.difference(hosts)
    if new_childs and recurse:
        rec_childs = get_child_hosts(site, new_childs, True)
        new_childs.update(rec_childs)
    return list(new_childs)

def paint_downtime_buttons(what):
    html.write(_('Downtime Comment')+": ")
    html.text_input("_down_comment", size=40, submit="")
    html.write("<hr>")
    html.button("_down_2h", _("2 hours"))
    html.button("_down_today", _("Today"))
    html.button("_down_week", _("This week"))
    html.button("_down_month", _("This month"))
    html.button("_down_year", _("This year"))
    html.write(" &nbsp; - &nbsp;")
    html.button("_down_remove", _("Remove all"))
    html.write("<hr>")
    html.button("_down_custom", _("Custom time range"))
    html.datetime_input("_down_from", time.time(), submit="_down_custom")
    html.write("&nbsp; "+_('to')+" &nbsp;")
    html.datetime_input("_down_to", time.time() + 7200, submit="_down_custom")
    html.write("<hr>")
    html.button("_down_from_now", _("From now for"))
    html.write("&nbsp;")
    html.number_input("_down_minutes", 60, size=4, submit="_down_from_now")
    html.write("&nbsp; " + _("minutes"))
    html.write("<hr>")
    html.checkbox("_down_flexible", False, label=_('flexible with max. duration')+" ")
    html.time_input("_down_duration", 2, 0)
    html.write(" "+_('(HH:MM)'))
    if what == "host":
        html.write("<hr>")
        html.checkbox("_include_childs", False, label=_('Also set downtime on child hosts'))
        html.write("  ")
        html.checkbox("_include_childs_recurse", False, label=_('Do this recursively'))


multisite_commands.append({
    "tables"      : [ "host" ],
    "permission"  : "action.downtimes",
    "title"       : _("Schedule downtimes"),
    "render"      : lambda: paint_downtime_buttons("host"),
    "action"      : command_downtime,
    "group"       : _("Downtimes"),
})

multisite_commands.append({
    "tables"      : [ "service" ],
    "permission"  : "action.downtimes",
    "title"       : _("Schedule downtimes"),
    "render"      : lambda: paint_downtime_buttons("service"),
    "action"      : command_downtime,
    "group"       : _("Downtimes"),
})

# REMOVE DOWNTIMES (table downtimes)
multisite_commands.append({
    "tables"      : [ "downtime" ],
    "permission"  : "action.downtimes",
    "title"       : _("Downtimes"),
    "render"      : lambda: \
        html.button("_remove_downtimes", _("Remove")),
    "action"      : lambda cmdtag, spec, row: \
      html.has_var("_remove_downtimes") and \
      ( "DEL_%s_DOWNTIME;%d" % (cmdtag, spec),
        _("remove"))
})

# REMOVE COMMENTS (table comments)
multisite_commands.append({
    "tables"      : [ "comment" ],
    "permission"  : "action.addcomment",
    "title"       : _("Comments"),
    "render"      : lambda: \
        html.button("_remove_comments", _("Remove")),
    "action"      : lambda cmdtag, spec, row: \
      html.has_var("_remove_comments") and \
      ( "DEL_%s_COMMENT;%d" % (cmdtag, spec),
        _("remove"))
})
