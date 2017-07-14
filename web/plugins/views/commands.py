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


#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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
        html.write_text(_("and spread over") + " ") == \
        html.number_input("_resched_spread", 0, size=3) == \
        html.write_text(" " + _("minutes") + " "),
    "action"      : command_reschedule,
    "row_stats"   : True, # Get information about number of rows and current row nr.
})


#.
#   .--Enable/Disable Notifications----------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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


#.
#   .--Enable/Disable Active Checks----------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |       _        _   _              ____ _               _             |
#   |      / \   ___| |_(_)_   _____   / ___| |__   ___  ___| | _____      |
#   |     / _ \ / __| __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|     |
#   |    / ___ \ (__| |_| |\ V /  __/ | |___| | | |  __/ (__|   <\__ \     |
#   |   /_/   \_\___|\__|_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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


#.
#   .--Enable/Disable Passive Checks---------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |   ____               _              ____ _               _           |
#   |  |  _ \ __ _ ___ ___(_)_   _____   / ___| |__   ___  ___| | _____    |
#   |  | |_) / _` / __/ __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|   |
#   |  |  __/ (_| \__ \__ \ |\ V /  __/ | |___| | | |  __/ (__|   <\__ \   |
#   |  |_|   \__,_|___/___/_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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



#.
#   .--Clear Modified Attributes-------------------------------------------.
#   |            ____ _                   __  __           _               |
#   |           / ___| | ___  __ _ _ __  |  \/  | ___   __| |              |
#   |          | |   | |/ _ \/ _` | '__| | |\/| |/ _ \ / _` |              |
#   |          | |___| |  __/ (_| | |    | |  | | (_) | (_| |_             |
#   |           \____|_|\___|\__,_|_|    |_|  |_|\___/ \__,_(_)            |
#   |                                                                      |
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

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


#.
#   .--Fake Checks---------------------------------------------------------.
#   |         _____     _           ____ _               _                 |
#   |        |  ___|_ _| | _____   / ___| |__   ___  ___| | _____          |
#   |        | |_ / _` | |/ / _ \ | |   | '_ \ / _ \/ __| |/ / __|         |
#   |        |  _| (_| |   <  __/ | |___| | | |  __/ (__|   <\__ \         |
#   |        |_|  \__,_|_|\_\___|  \____|_| |_|\___|\___|_|\_\___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

config.declare_permission("action.fakechecks",
        _("Fake check results"),
        _("Manually submit check results for host and service checks"),
        [ "admin" ])

def command_fake_checks(cmdtag, spec, row):
    for s in [0, 1, 2, 3]:
        statename = html.var("_fake_%d" % s)
        if statename:
            pluginoutput = html.get_unicode_input("_fake_output").strip()
            if not pluginoutput:
                pluginoutput = _("Manually set to %s by %s") % (html.attrencode(statename), config.user.id)
            perfdata = html.var("_fake_perfdata")
            if perfdata:
                pluginoutput += "|" + perfdata
            if cmdtag == "SVC":
                cmdtag = "SERVICE"
            command = "PROCESS_%s_CHECK_RESULT;%s;%s;%s" % (cmdtag, spec, s, lqencode(pluginoutput))
            title = _("<b>manually set check results to %s</b> for") % html.attrencode(statename)
            return command, title


def render_fake_form(what):
    html.open_table()

    html.open_tr()
    html.open_td()
    html.write_text("%s: " % _("Plugin output"))
    html.close_td()
    html.open_td()
    html.text_input("_fake_output", "", size=50)
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td()
    html.write_text("%s: " % _("Performance data"))
    html.close_td()
    html.open_td()
    html.text_input("_fake_perfdata", "", size=50)
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td()
    html.write_text(_("Result:"))
    html.close_td()
    html.open_td()
    if what == "host":
        html.button("_fake_0", _("Up"))
        html.button("_fake_1", _("Down"))
    else:
        html.button("_fake_0", _("OK"))
        html.button("_fake_1", _("Warning"))
        html.button("_fake_2", _("Critical"))
        html.button("_fake_3", _("Unknown"))
    html.close_td()
    html.close_tr()

    html.close_table()

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


#.
#   .--Custom Notifications------------------------------------------------.
#   |                   ____          _                                    |
#   |                  / ___|   _ ___| |_ ___  _ __ ___                    |
#   |                 | |  | | | / __| __/ _ \| '_ ` _ \                   |
#   |                 | |__| |_| \__ \ || (_) | | | | | |                  |
#   |                  \____\__,_|___/\__\___/|_| |_| |_|                  |
#   |                                                                      |
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

config.declare_permission("action.customnotification",
        _("Send custom notification"),
        _("Manually let the core send a notification to a host or service in order "
          "to test if notifications are setup correctly"),
        [ "user", "admin" ])

def command_custom_notification(cmdtag, spec, row):
    if html.var("_customnotification"):
        comment = html.get_unicode_input("_cusnot_comment")
        broadcast = html.get_checkbox("_cusnot_broadcast") and 1 or 0
        forced = html.get_checkbox("_cusnot_forced") and 2 or 0
        command = "SEND_CUSTOM_%s_NOTIFICATION;%s;%s;%s;%s" % \
                ( cmdtag, spec, broadcast + forced, config.user.id, lqencode(comment))
        title = _("<b>send a custom notification</b> regarding")
        return command, title


multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.customnotification",
    "title"       : _("Custom notification"),
    "render"      : lambda: \
        html.write_text(_('Comment') + ": ") == \
        html.text_input("_cusnot_comment", "TEST", size=20, submit="_customnotification") == \
        html.write(" &nbsp; ") == \
        html.checkbox("_cusnot_forced", False, label=_("forced")) == \
        html.checkbox("_cusnot_broadcast", False, label=_("broadcast")) == \
        html.write(" &nbsp; ") == \
        html.button("_customnotification", _('Send')),
    "action"      : command_custom_notification,
})


#.
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   '----------------------------------------------------------------------'

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
        comment = html.get_unicode_input("_ack_comment")
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
            expire_text = ";%d" % expire
        else:
            expire_text = ""

        def make_command(spec, cmdtag):
            return "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;%d;%d;%d;%s" % \
                          (spec, sticky, sendnot, perscomm, config.user.id) + (";%s" % lqencode(comment)) \
                          + expire_text

        if "aggr_tree" in row: # BI mode
            commands = [(site, make_command(spec, cmdtag)) for (site, spec, cmdtag) in specs ]
        else:
            commands = [ make_command(spec, cmdtag) ]

        title = _("<b>acknowledge the problems%s</b> of") % \
                    (expire_text and (_(" for a period of %s") % Age().value_to_text(expire_secs)) or "")
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
        html.hr() == \
        html.checkbox("_ack_sticky",
                      config.view_action_defaults["ack_sticky"],
                      label=_("sticky")) == \
        html.checkbox("_ack_notify",
                      config.view_action_defaults["ack_notify"],
                      label=_("send notification")) == \
        html.checkbox("_ack_persistent",
                      config.view_action_defaults["ack_persistent"],
                      label=_('persistent comment')) == \
        html.hr() == \
        Age(display=["days", "hours", "minutes"], label=_("Expire acknowledgement after")).render_input("_ack_expire", 0) == \
        html.help(_("Note: Expiration of acknowledgements only works when using the Check_MK Micro Core.")) == \
        html.hr() == \
        html.write_text(_("Comment") + ": ") == \
        html.text_input("_ack_comment", size=48, submit="_acknowledge"),
    "action"      : command_acknowledgement,
    "group"       : _("Acknowledge"),
})


#.
#   .--Comments------------------------------------------------------------.
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

config.declare_permission("action.addcomment",
        _("Add comments"),
        _("Add comments to hosts or services, and remove comments"),
        [ "user", "admin" ])

def command_comment(cmdtag, spec, row):
    if html.var("_add_comment"):
        comment = html.get_unicode_input("_comment")
        if not comment:
            raise MKUserError("_comment", _("You need to supply a comment."))
        command = "ADD_" + cmdtag + "_COMMENT;%s;1;%s" % \
                  (spec, config.user.id) + (";%s" % lqencode(comment))
        title = _("<b>add a comment to</b>")
        return command, title

multisite_commands.append({
    "tables"      : [ "host", "service" ],
    "permission"  : "action.addcomment",
    "title"       : _("Add comment"),
    "render"      : lambda: \
        html.write_text(_('Comment')+": ") == \
        html.text_input("_comment", size=33, submit="_add_comment") == \
        html.write(" &nbsp; ") == \
        html.button("_add_comment", _("Add comment")),
    "action"      : command_comment,
})


#.
#   .--Downtimes-----------------------------------------------------------.
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

config.declare_permission("action.downtimes",
        _("Set/Remove Downtimes"),
        _("Schedule and remove downtimes on hosts and services"),
        [ "user", "admin" ])


def get_duration_human_readable(secs):
    days, rest  = divmod(secs, 86400)
    hours, rest = divmod(rest, 3600)
    mins, secs  = divmod(rest, 60)

    return ", ".join(["%d %s" % (val, label)
                      for val, label in [(days, "days"),
                                         (hours, "hours"),
                                         (mins, "minutes"),
                                         (secs, "seconds")]
                      if val > 0])


def command_downtime(cmdtag, spec, row):
    down_from = int(time.time())
    down_to = None

    if has_recurring_downtimes() and html.get_checkbox("_down_do_recur"):
        recurring_type = int(html.var("_down_recurring"))
        title_start = _("schedule a periodic downtime every %s") % wato.recurring_downtimes_types[recurring_type]
    else:
        title_start = _("schedule an immediate downtime")

    rangebtns = html.all_varnames_with_prefix("_downrange")

    def resolve_end(name):
        now = time.localtime(down_from)
        if name == "next_day":
            return time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1, \
                _("<b>%s until 24:00:00</b> on") % title_start
        elif name == "next_week":
            wday = now.tm_wday
            days_plus = 6 - wday
            res = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
            res += days_plus * 24 * 3600
            return res, _("<b>%s until sunday night</b> on") % title_start
        elif name == "next_month":
            new_month = now.tm_mon + 1
            if new_month == 13:
                new_year = now.tm_year + 1
                new_month = 1
            else:
                new_year = now.tm_year
            return time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, now.tm_isdst)), \
                _("<b>%s until end of month</b> on") % title_start
        elif name == "next_year":
            return time.mktime((now.tm_year, 12, 31, 23, 59, 59, 0, 0, now.tm_isdst)) + 1, \
                _("<b>%s until end of %d</b> on") % (title_start, now.tm_year)
        else:
            duration = int(name)
            return down_from + duration, \
                _("<b>%s of %s length</b> on") %\
                (title_start, get_duration_human_readable(duration))

    try:
        rangebtn = rangebtns.next()
    except StopIteration:
        rangebtn = None

    if rangebtn:
        btnname, end = rangebtn.split("__", 1)
        down_to, title = resolve_end(end)
    elif html.var("_down_from_now"):
        try:
            minutes = int(html.var("_down_minutes"))
        except:
            minutes = 0

        if minutes <= 0:
            raise MKUserError("_down_minutes", _("Please enter a positive number of minutes."))

        down_to = time.time() + minutes * 60
        title = _("<b>%s for the next %d minutes</b> on") % (title_start, minutes)

    elif html.var("_down_adhoc"):
        minutes = config.adhoc_downtime.get("duration",0)
        down_to = time.time() + minutes * 60
        title = _("<b>%s for the next %d minutes</b> on") % (title_start, minutes)

    elif html.var("_down_custom"):
        down_from = html.get_datetime_input("_down_from")
        down_to   = html.get_datetime_input("_down_to")
        if down_to < time.time():
            raise MKUserError("_down_to", _("You cannot set a downtime that ends in the past. "
                         "This incident will be reported."))

        if down_to < down_from:
            raise MKUserError("_down_to", _("Your end date is before your start date."))

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
            comment = html.get_unicode_input("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        if html.var("_down_flexible"):
            fixed = 0
            duration = html.get_time_input("_down_duration", _("the duration"))
        else:
            fixed = 1
            duration = 0

        if html.get_checkbox("_down_do_recur"):
            fixed_and_recurring = recurring_type * 2 + fixed
        else:
            fixed_and_recurring = fixed

        def make_command(spec, cmdtag):
            return ("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % spec ) \
                   + ("%d;%d;%d;0;%d;%s;" % (down_from, down_to, fixed_and_recurring, duration, config.user.id)) \
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
    sites.live().set_only_sites([site])
    query = "GET hosts\nColumns: name\n"
    for h in hosts:
        query += "Filter: parents >= %s\n" % h
    query += "Or: %d\n" % len(hosts)
    childs = sites.live().query_column(query)
    sites.live().set_only_sites(None)
    # Recursion, but try to avoid duplicate work
    childs = set(childs)
    new_childs = childs.difference(hosts)
    if new_childs and recurse:
        rec_childs = get_child_hosts(site, new_childs, True)
        new_childs.update(rec_childs)
    return list(new_childs)


def paint_downtime_buttons(what):
    html.write_text(_('Downtime Comment')+": ")
    html.text_input("_down_comment", "", size=60, submit="")
    html.hr()
    html.button("_down_from_now", _("From now for"))
    html.write("&nbsp;")
    html.number_input("_down_minutes", 60, size=4, submit="_down_from_now")
    html.write("&nbsp; " + _("minutes"))
    html.hr()
    for time_range in config.user_downtime_timeranges:
        html.button("_downrange__%s" % time_range['end'], _u(time_range['title']))
    if what != "aggr":
        html.write(" &nbsp; - &nbsp;")
        html.button("_down_remove", _("Remove all"))
    html.hr()
    if config.adhoc_downtime and config.adhoc_downtime.get("duration"):
        adhoc_duration = config.adhoc_downtime.get("duration")
        adhoc_comment  = config.adhoc_downtime.get("comment", "")
        html.button("_down_adhoc", _("Adhoc for %d minutes") % adhoc_duration)
        html.write("&nbsp;")
        html.write_text(_('with comment')+": ")
        html.write(adhoc_comment)
        html.hr()

    html.button("_down_custom", _("Custom time range"))
    html.datetime_input("_down_from", time.time(), submit="_down_custom")
    html.write("&nbsp; "+_('to')+" &nbsp;")
    html.datetime_input("_down_to", time.time() + 7200, submit="_down_custom")
    html.hr()
    html.checkbox("_down_flexible", False, label=_('flexible with max. duration')+" ")
    html.time_input("_down_duration", 2, 0)
    html.write_text(" "+_('(HH:MM)'))
    if what == "host":
        html.hr()
        html.checkbox("_include_childs", False, label=_('Also set downtime on child hosts'))
        html.write_text("  ")
        html.checkbox("_include_childs_recurse", False, label=_('Do this recursively'))
    elif what == "service":
        html.hr()
        html.checkbox("_on_hosts", False, label=_('Schedule downtimes on the affected '
                                                  '<b>hosts</b> instead of on the individual '
                                                  'services'))

    if has_recurring_downtimes():
        html.hr()
        html.checkbox("_down_do_recur", False,
                      label=_("Repeat this downtime on a regular base every"))
        html.write_text(" ")
        recurring_selections = [ (str(k), v) for (k,v) in
                                 sorted(wato.recurring_downtimes_types.items())]
        html.select("_down_recurring", recurring_selections, "3")
        html.write_text(_("(This only works when using CMC)"))


def has_recurring_downtimes():
    try:
        wato.recurring_downtimes_types # Check if this exists
        return True
    except AttributeError:
        return False
    except NameError:
        return False


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
    "title"       : _("Remove downtimes"),
    "render"      : lambda: html.button("_remove_downtimes", _("Remove")),
    "action"      : lambda cmdtag, spec, row: html.has_var("_remove_downtimes") and \
                           ( "DEL_%s_DOWNTIME;%d" % (cmdtag, spec), _("remove"))
})

# REMOVE COMMENTS (table comments)

def remove_comments(cmdtag, spec, row):
    if html.has_var("_remove_comments"):
        commands = [("DEL_%s_COMMENT;%d" % (cmdtag, spec))]
        if row.get("comment_entry_type") == 4:
            if row.get("service_description"):
                commands.append(("REMOVE_%s_ACKNOWLEDGEMENT;%s;%s" %\
                                (cmdtag, row["host_name"], row["service_description"])))
            else:
                commands.append(("REMOVE_%s_ACKNOWLEDGEMENT;%s" %\
                                (cmdtag, row["host_name"])))

        return commands, _("remove")

multisite_commands.append({
    "tables"      : [ "comment" ],
    "permission"  : "action.addcomment",
    "title"       : _("Remove comments"),
    "render"      : lambda: html.button("_remove_comments", _("Remove")),
    "action"      : remove_comments
})

#.
#   .--Stars * (Favorites)-------------------------------------------------.
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
    stars = config.user.load_stars()
    if star == "0" and spec in stars:
        stars.remove(spec)
    elif star == "1":
        stars.add(spec)
    config.user.save_stars(stars)

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


#.
#   .--Failed Notifications------------------------------------------------.
#   |                      _____     _ _          _                        |
#   |                     |  ___|_ _(_) | ___  __| |                       |
#   |                     | |_ / _` | | |/ _ \/ _` |                       |
#   |                     |  _| (_| | | |  __/ (_| |                       |
#   |                     |_|  \__,_|_|_|\___|\__,_|                       |
#   |                                                                      |
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def command_acknowledge_failed_notification(cmdtag, spec, row):
    return str(row['log_time']), _("<b>acknowledge failed notifications up to</b>")

def executor_acknowledge_failed_notification(command, site):
    import notifications
    acktime = int(command)
    notifications.acknowledge_failed_notifications(acktime)

multisite_commands.append({
    "tables"     : [ "log" ],
    "permission" : "general.acknowledge_failed_notifications",
    "title"      : _("Acknowledge"),
    "render"     : lambda: html.button("_acknowledge_failed_notification", _("Acknowledge")),
    "action"     : command_acknowledge_failed_notification,
    "executor"   : executor_acknowledge_failed_notification
})

