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

# RESCHEDULE ACTIVE CHECKS
def command_reschedule(cmdtag, spec, row, row_nr, total_rows):
    if html.var("_resched_checks"):
        spread = saveint(html.var("_resched_spread"))
        text = "<b>" + _("reschedule an immediate check")
        if spread:
            text += _(" spread over %d minutes ") % spread

        text += "</b>" + _("of")

        t = time.time()
        if spread:
            t += spread * 60.0 * row_nr / total_rows

        command = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(t))
        return command, text

config.declare_permission("action.reschedule",
        _("Reschedule checks"),
        _("Reschedule host and service checks"),
        [ "user", "admin" ])


multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.reschedule",
    "title"       : _("Reschedule active checks"),
    "render"      : lambda: \
        html.button("_resched_checks", _("Reschedule")) == \
        html.write(_("and spread over") + " ") == \
        html.number_input("_resched_spread", 0, size=3) == \
        html.write(" " + _("minutes") + " "),
    "action"      : command_reschedule,
    "row_stats"   : True, # Get information about number of rows and current row nr.
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
        _("Reset modified attributes"),
        _("Reset all manually modified attributes of a host or service (like disabled notifications)"),
        [ "admin" ])

multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.clearmodattr",
    "title"       : _("Modified attributes"),
    "render"      : lambda: \
       html.button("_clear_modattr", _('Clear modified attributes')),
    "action"      : lambda cmdtag, spec, row: (
        html.var("_clear_modattr") and (
        "CHANGE_" + cmdtag + "_MODATTR;%s;0" % spec,
         _("<b>clear the modified attributes</b> of"))),
})

# FAKE CHECKS
config.declare_permission("action.fakechecks",
        _("Fake check results"),
        _("Manually submit check results for host and service checks"),
        [ "admin" ])

def command_fake_checks(cmdtag, spec, row):
    for s in [0, 1, 2, 3]:
        statename = html.var("_fake_%d" % s)
        if statename:
            pluginoutput = html.var_utf8("_fake_output").strip()
            if not pluginoutput:
                pluginoutput = _("Manually set to %s by %s") % (html.attrencode(statename), config.user_id)
            perfdata = html.var("_fake_perfdata")
            if perfdata:
                pluginoutput += "|" + perfdata
            if cmdtag == "SVC":
                cmdtag = "SERVICE"
            command = "PROCESS_%s_CHECK_RESULT;%s;%s;%s" % (cmdtag, spec, s, lqencode(pluginoutput))
            title = _("<b>manually set check results to %s</b> for") % html.attrencode(statename)
            return command, title


def render_fake_form(what):
    html.write("<table><tr><td>")
    html.write("%s: " % _("Plugin output"))
    html.write("</td><td>")
    html.text_input("_fake_output", "", size=50)
    html.write("</td></tr><tr><td>")
    html.write("%s: " % _("Performance data"))
    html.write("</td><td>")
    html.text_input("_fake_perfdata", "", size=50)
    html.write("</td></tr><tr><td>")
    html.write(_("Set to:"))
    html.write("</td><td>")
    if what == "host":
        html.button("_fake_0", _("Up"))
        html.button("_fake_1", _("Down"))
        html.button("_fake_2", _("Unreachable"))
    else:
        html.button("_fake_0", _("OK"))
        html.button("_fake_1", _("Warning"))
        html.button("_fake_2", _("Critical"))
        html.button("_fake_3", _("Unknown"))
    html.write("</td></tr></table>")

multisite_commands.append({
    "tables"      : [ "host" ],
    "permission"  : "action.fakechecks",
    "title"       : _("Fake check results"),
    "group"       : _("Fake check results"),
    "render"      : lambda: render_fake_form("host"),
    "action"      : command_fake_checks,
})

multisite_commands.append({
    "tables"      : [ "service" ],
    "permission"  : "action.fakechecks",
    "title"       : _("Fake check results"),
    "group"       : _("Fake check results"),
    "render"      : lambda: render_fake_form("service"),
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
                ( cmdtag, spec, broadcast + forced, config.user_id, lqencode(comment))
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
    if "aggr_tree" in row: # BI mode
        specs = []
        for site, host, service in bi.find_all_leaves(row["aggr_tree"]):
            if service:
                spec = "%s;%s" % (host, service)
                cmdtag = "SVC"
            else:
                spec = host
                cmdtag = "HOST"
            specs.append((site, spec, cmdtag))

    if html.var("_acknowledge"):
        comment = html.var_utf8("_ack_comment")
        if not comment:
            raise MKUserError("_ack_comment", _("You need to supply a comment."))
        if ";" in comment:
            raise MKUserError("_ack_comment", _("The comment must not contain semicolons."))
        sticky = html.var("_ack_sticky") and 2 or 0
        sendnot = html.var("_ack_notify") and 1 or 0
        perscomm = html.var("_ack_persistent") and 1 or 0

        expire_secs = Age().from_html_vars("_ack_expire")
        if expire_secs:
            expire = int(time.time()) + expire_secs
        else:
            expire = 0

        def make_command(spec, cmdtag):
            return "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;%d;%d;%d;%s" % \
                          (spec, sticky, sendnot, perscomm, config.user_id) + (";%s" % lqencode(comment)) \
                          + (";%d" % expire)

        if "aggr_tree" in row: # BI mode
            commands = [(site, make_command(spec, cmdtag)) for (site, spec, cmdtag) in specs ]
        else:
            commands = [ make_command(spec, cmdtag) ]

        title = _("<b>acknowledge the problems%s</b> of") % \
                    (expire and (_(" for a period of %s") % Age().value_to_text(expire_secs)) or "")
        return commands, title

    elif html.var("_remove_ack"):
        def make_command(spec, cmdtag):
            return "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec

        if "aggr_tree" in row: # BI mode
            commands = [(site, make_command(spec, cmdtag)) for (site, spec, cmdtag) in specs ]
        else:
            commands = [ make_command(spec, cmdtag) ]
        title = _("<b>remove acknowledgements</b> from")
        return commands, title


multisite_commands.append({
    "tables"      : [ "host", "service", "aggr" ],
    "permission"  : "action.acknowledge",
    "title"       : _("Acknowledge Problems"),
    "render"      : lambda: \
        html.button("_acknowledge", _("Acknowledge")) == \
        html.button("_remove_ack", _("Remove Acknowledgement")) == \
        html.write("<hr>") == \
        html.checkbox("_ack_sticky", True, label=_("sticky")) == \
        html.checkbox("_ack_notify", True, label=_("send notification")) == \
        html.checkbox("_ack_persistent", False, label=_('persistent comment')) == \
        html.write("<hr>") == \
        Age(display=["days", "hours", "minutes"], label=_("Expire acknowledgement after")).render_input("_ack_expire", 0) == \
        html.help(_("Note: Expiration of acknowledgements only works when using the Check_MK Micro Core.")) == \
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
                  (spec, config.user_id) + (";%s" % lqencode(comment))
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

    elif html.var("_down_adhoc"):
        minutes = config.adhoc_downtime.get("duration",0)
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
        if html.var("_on_hosts"):
            raise MKUserError("_on_hosts", _("The checkbox for setting host downtimes does not work when removing downtimes."))

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
        if html.var("_down_adhoc"):
            comment = config.adhoc_downtime.get("comment","")
        else:
            comment = html.var_utf8("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        if html.var("_down_flexible"):
            fixed = 0
            duration = html.get_time_input("_down_duration", _("the duration"))
        else:
            fixed = 1
            duration = 0

        def make_command(spec, cmdtag):
            return ("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % spec ) \
                   + ("%d;%d;%d;0;%d;%s;" % (down_from, down_to, fixed, duration, config.user_id)) \
                   + lqencode(comment)

        if "aggr_tree" in row: # BI mode
            commands = []
            for site, host, service in bi.find_all_leaves(row["aggr_tree"]):
                if service:
                    spec = "%s;%s" % (host, service)
                    cmdtag = "SVC"
                else:
                    spec = host
                    cmdtag = "HOST"
                commands.append((site, make_command(spec, cmdtag)))
        else:
            if html.var("_include_childs"): # only for hosts
                specs = [ spec ] + get_child_hosts(row["site"], [spec], recurse = not not html.var("_include_childs_recurse"))
            elif html.var("_on_hosts"): # set on hosts instead of services
                specs = [ spec.split(";")[0] ]
                title += " the hosts of"
                cmdtag = "HOST"
            else:
                specs = [ spec ]

            commands = [ make_command(spec, cmdtag) for spec in  specs ]

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
    html.text_input("_down_comment", "", size=60, submit="")
    html.write("<hr>")
    html.button("_down_from_now", _("From now for"))
    html.write("&nbsp;")
    html.number_input("_down_minutes", 60, size=4, submit="_down_from_now")
    html.write("&nbsp; " + _("minutes"))
    html.write("<hr>")
    html.button("_down_2h", _("2 hours"))
    html.button("_down_today", _("Today"))
    html.button("_down_week", _("This week"))
    html.button("_down_month", _("This month"))
    html.button("_down_year", _("This year"))
    if what != "aggr":
        html.write(" &nbsp; - &nbsp;")
        html.button("_down_remove", _("Remove all"))
    html.write("<hr>")
    if config.adhoc_downtime and config.adhoc_downtime.get("duration"):
        adhoc_duration = config.adhoc_downtime.get("duration")
        adhoc_comment  = config.adhoc_downtime.get("comment", "")
        html.button("_down_adhoc", _("Adhoc for %d minutes") % adhoc_duration)
        html.write("&nbsp;")
        html.write(_('with comment')+": ")
        html.write(adhoc_comment)
        html.write("<hr>")

    html.button("_down_custom", _("Custom time range"))
    html.datetime_input("_down_from", time.time(), submit="_down_custom")
    html.write("&nbsp; "+_('to')+" &nbsp;")
    html.datetime_input("_down_to", time.time() + 7200, submit="_down_custom")
    html.write("<hr>")
    html.checkbox("_down_flexible", False, label=_('flexible with max. duration')+" ")
    html.time_input("_down_duration", 2, 0)
    html.write(" "+_('(HH:MM)'))
    if what == "host":
        html.write("<hr>")
        html.checkbox("_include_childs", False, label=_('Also set downtime on child hosts'))
        html.write("  ")
        html.checkbox("_include_childs_recurse", False, label=_('Do this recursively'))
    elif what == "service":
        html.write("<hr>")
        html.checkbox("_on_hosts", False, label=_('Schedule downtimes on the affected <b>hosts</b> instead of their services'))



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

multisite_commands.append({
    "tables"      : [ "aggr" ],
    "permission"  : "action.downtimes",
    "title"       : _("Schedule downtimes"),
    "render"      : lambda: paint_downtime_buttons("aggr"),
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

#   .--Stars *-------------------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def command_star(cmdtag, spec, row):
    if html.var("_star") or html.var("_unstar"):
        star = html.var("_star") and 1 or 0
        if star:
            title = _("<b>add to you favorites</b>")
        else:
            title = _("<b>remove from your favorites</b>")
        return "STAR;%d;%s" % (star, spec), title


def command_executor_star(command, site):
    foo, star, spec = command.split(";", 2)
    stars = config.load_stars()
    if star == "0" and spec in stars:
        stars.remove(spec)
    elif star == "1":
        stars.add(spec)
    config.save_stars(stars)

config.declare_permission("action.star",
    _("Use favorites"),
    _("This permission allows a user to make certain host and services "
      "his personal favorites. Favorites can be used for a having a fast "
      "access to items that are needed on a regular base."),
    [ "user", "admin" ])

multisite_commands.append({
    "tables"         : [ "host", "service" ],
    "permission"     : "action.star",
    "title"          : _("Favorites"),
    "render"         : lambda: \
       html.button("_star",   _("Add to Favorites")) == \
       html.button("_unstar", _("Remove from Favorites")),
    "action"         : command_star,
    "executor"       : command_executor_star,
})

