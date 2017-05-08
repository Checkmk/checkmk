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

import sites
import mkeventd
from valuespec import *
from cmk.defines import short_service_state_name

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

#   .--Datasources---------------------------------------------------------.
#   |       ____        _                                                  |
#   |      |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___         |
#   |      | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|        |
#   |      | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \        |
#   |      |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def query_ec_table(datasource, columns, add_columns, query, only_sites, limit, tablename):
    if "event_contact_groups" not in columns:
        columns.append("event_contact_groups")
    if "host_contact_groups" not in columns:
        columns.append("host_contact_groups")

    rows = query_data(datasource, columns, add_columns, query, only_sites, limit,
                      tablename=tablename)

    if not rows:
        return rows

    _ec_filter_host_information_of_not_permitted_hosts(rows)

    if config.user.may("mkeventd.seeunrelated"):
        return rows # user is allowed to see all events returned by the core

    return [ r for r in rows if r["event_contact_groups"] != [] or r["host_name"] != "" ]


# Handle the case where a user is allowed to see all events (-> events for hosts he
# is not permitted for). In this case the user should be allowed to see the event
# information, but not the host related information.
#
# To realize this, whe filter all data from the host_* columns from the response.
# See Gitbug #2462 for some more information.
#
# This should be handled in the core, but the core does not know anything about
# the "mkeventd.seeall" permissions. So it is simply not possible to do this on
# core level at the moment.
def _ec_filter_host_information_of_not_permitted_hosts(rows):
    if not config.user.may("mkeventd.seeall"):
        return

    user_groups = set(config.user.contact_groups())

    def is_contact(row):
        return bool(user_groups.intersection(row["host_contact_groups"]))

    if rows:
        remove_keys = [ c for c in rows[0].keys() if c.startswith("host_") ]
    else:
        remove_keys = []

    for row in rows:
        if row["host_name"] == "":
            continue # This is an "unrelated host", don't treat it here

        if is_contact(row):
            continue # The user may see these host information

        # Now remove the host information. This can sadly not apply the cores
        # default values for the different columns. We try our best to clean up
        for key in remove_keys:
            if type(row[key]) == list:
                row[key] = []
            elif type(row[key]) == int:
                row[key] = 0
            elif type(row[key]) == float:
                row[key] = 0.0
            elif type(row[key]) == str:
                row[key] = ""
            elif type(row[key]) == unicode:
                row[key] = u""


# Declare datasource only if the event console is activated. We do
# not want to irritate users that do not know anything about the EC.
if mkeventd_enabled:
    config.declare_permission("mkeventd.seeall",
            _("See all events"),
            _("If a user lacks this permission then he/she can see only those events that "
              "originate from a host that he/she is a contact for."),
            [ "user", "admin", "guest" ])

    config.declare_permission("mkeventd.seeunrelated",
           _("See events not related to a known host"),
           _("If that user does not have the permission <i>See all events</i> then this permission "
             "controls wether he/she can see events that are not related to a host in the monitoring "
             "and that do not have been assigned specific contact groups to via the event rule."),
           [ "user", "admin", "guest" ])

    multisite_datasources["mkeventd_events"] = {
        "title"       : _("Event Console: Current Events"),
        "table"       : (query_ec_table, ["eventconsoleevents"]),
        "auth_domain" : "ec",
        "infos"       : [ "event", "host" ],
        "keys"        : [],
        "idkeys"      : [ 'site', 'host_name', 'event_id' ],
        "time_filters" : [ "event_first" ],
    }

    multisite_datasources["mkeventd_history"] = {
        "title"       : _("Event Console: Event History"),
        "table"       : (query_ec_table, ["eventconsolehistory"]),
        "auth_domain" : "ec",
        "infos"       : [ "history", "event", "host" ],
        "keys"        : [],
        "idkeys"      : [ 'site', 'host_name', 'event_id', 'history_line' ],
        "time_filters" : [ "history_time" ],
    }


    #.
    #   .--Painters------------------------------------------------------------.
    #   |                 ____       _       _                                 |
    #   |                |  _ \ __ _(_)_ __ | |_ ___ _ __ ___                  |
    #   |                | |_) / _` | | '_ \| __/ _ \ '__/ __|                 |
    #   |                |  __/ (_| | | | | | ||  __/ |  \__ \                 |
    #   |                |_|   \__,_|_|_| |_|\__\___|_|  |___/                 |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    multisite_painters["event_id"] = {
        "title"   : _("ID of the event"),
        "short"   : _("ID"),
        "columns" : ["event_id"],
        "paint"   : lambda row: ("number", str(row["event_id"])),
    }

    multisite_painters["event_count"] = {
        "title"   : _("Count (number of recent occurrances)"),
        "short"   : _("Cnt."),
        "columns" : ["event_count"],
        "paint"   : lambda row: ("number", str(row["event_count"])),
    }

    multisite_painters["event_text"] = {
        "title"   : _("Text/Message of the event"),
        "short"   : _("Message"),
        "columns" : ["event_text"],
        "paint"   : lambda row: ("", html.attrencode(row["event_text"]).replace("\x01","<br>")),
    }

    def paint_ec_match_groups(row):
        groups = row["event_match_groups"]
        if groups:
            code = ""
            for text in groups:
                code += '<span>%s</span>' % text
            return "matchgroups", code
        else:
            return "", ""

    multisite_painters["event_match_groups"] = {
        "title"   : _("Match Groups"),
        "short"   : _("Match"),
        "columns" : ["event_match_groups"],
        "paint"   : paint_ec_match_groups,
    }

    multisite_painters["event_first"] = {
        "title"   : _("Time of first occurrance of this serial"),
        "short"   : _("First"),
        "columns" : ["event_first"],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["event_first"], True, True),
    }

    multisite_painters["event_last"] = {
        "title"   : _("Time of last occurrance"),
        "short"   : _("Last"),
        "columns" : ["event_last"],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["event_last"], True, True),
    }

    multisite_painters["event_comment"] = {
        "title"   : _("Comment to the event"),
        "short"   : _("Comment"),
        "columns" : ["event_comment"],
        "paint"   : lambda row: ("", row["event_comment"]),
    }

    def mkeventd_paint_sl(row):
        try:
            return "", dict(config.mkeventd_service_levels)[row["event_sl"]]
        except:
            return "", str(row["event_sl"])

    multisite_painters["event_sl"] = {
        "title"   : _("Service-Level"),
        "short"   : _("Level"),
        "columns" : ["event_sl"],
        "paint"   : mkeventd_paint_sl,
    }

    def paint_event_host(row):
        if row["host_name"]:
            return "", row["host_name"]
        else:
            return "", row["event_host"]

    multisite_painters["event_host"] = {
        "title"   : _("Hostname"),
        "short"   : _("Host"),
        "columns" : ["event_host", "host_name"],
        "paint"   : paint_event_host,
    }

    multisite_painters["event_ipaddress"] = {
        "title"   : _("Original IP-Address"),
        "short"   : _("Orig. IP"),
        "columns" : ["event_ipaddress"],
        "paint"   : lambda row: ("", row["event_ipaddress"]),
    }

    multisite_painters["event_owner"] = {
        "title"   : _("Owner of event"),
        "short"   : _("owner"),
        "columns" : ["event_owner"],
        "paint"   : lambda row: ("", row["event_owner"]),
    }

    multisite_painters["event_contact"] = {
        "title"   : _("Contact Person"),
        "short"   : _("Contact"),
        "columns" : ["event_contact" ],
        "paint"   : lambda row: ("", row["event_contact"]),
    }

    multisite_painters["event_application"] = {
        "title"   : _("Application / Syslog-Tag"),
        "short"   : _("Application"),
        "columns" : ["event_application" ],
        "paint"   : lambda row: ("", row["event_application"]),
    }

    multisite_painters["event_pid"] = {
        "title"   : _("Process ID"),
        "short"   : _("PID"),
        "columns" : ["event_pid" ],
        "paint"   : lambda row: ("", row["event_pid"]),
    }

    multisite_painters["event_priority"] = {
        "title"   : _("Syslog-Priority"),
        "short"   : _("Prio"),
        "columns" : ["event_priority" ],
        "paint"   : lambda row: ("", dict(mkeventd.syslog_priorities)[row["event_priority"]]),
    }

    multisite_painters["event_facility"] = {
        "title"   : _("Syslog-Facility"),
        "short"   : _("Facility"),
        "columns" : ["event_facility" ],
        "paint"   : lambda row: ("", dict(mkeventd.syslog_facilities)[row["event_facility"]]),
    }

    def paint_rule_id(row):
        rule_id = row["event_rule_id"]
        if config.user.may("mkeventd.edit"):
            urlvars = html.urlencode_vars([("mode", "mkeventd_edit_rule"), ("rule_id", rule_id)])
            return "", '<a href="wato.py?%s">%s</a>' % (urlvars, rule_id)
        else:
            return "", rule_id

    multisite_painters["event_rule_id"] = {
        "title"   : _("Rule-ID"),
        "short"   : _("Rule"),
        "columns" : ["event_rule_id" ],
        "paint"   : paint_rule_id,
    }

    def paint_event_state(row):
        state = row["event_state"]
        name = short_service_state_name(state, "")
        return "state svcstate state%s" % state, name

    multisite_painters["event_state"] = {
        "title"   : _("State (severity) of event"),
        "short"   : _("State"),
        "columns" : ["event_state"],
        "paint"   : paint_event_state,
    }

    multisite_painters["event_phase"] = {
        "title"   : _("Phase of event (open, counting, etc.)"),
        "short"   : _("Phase"),
        "columns" : ["event_phase" ],
        "paint"   : lambda row: ("", mkeventd.phase_names.get(row["event_phase"], ''))
    }

    def render_event_phase_icons(row):
        phase = row["event_phase"]

        if phase == "ack":
            title = _("This event has been acknowledged.")
        elif phase == "counting":
            title = _("This event has not reached the target count yet.")
        elif phase == "delayed":
            title = _("The action of this event is still delayed in the hope of a cancelling event.")
        else:
            return ''

        return html.render_icon(phase, help=title)

    def render_delete_event_icons(row):
        if config.user.may("mkeventd.delete"):
            urlvars = []

            # Found no cleaner way to get the view. Sorry.
            # TODO: This needs to be cleaned up with the new view implementation.
            if html.has_var("name") and html.has_var("id"):
                ident = int(html.var("id"))

                import dashboard
                dashboard.load_dashboards()
                view = dashboard.get_dashlet(html.var("name"), ident)

                # These actions are not performed within the dashlet. Assume the title url still
                # links to the source view where the action can be performed.
                title_url = view.get("title_url")
                if title_url:
                    from urlparse import urlparse, parse_qsl
                    url = urlparse(title_url)
                    filename = url.path
                    urlvars += parse_qsl(url.query)
            else:
                # Regular view
                view = permitted_views()[(html.var("view_name"))]
                target = None
                filename = None

            urlvars += [
                ("filled_in", "actions"),
                ("actions", "yes"),
                ("_do_actions", "yes"),
                ("_row_id", row_id(view, row)),
                ("_delete_event", _("Archive Event")),
                ("_show_result", "0"),
            ]
            url = html.makeactionuri(urlvars, filename=filename,
                                     delvars=["selection", "show_checkboxes"])
            return html.render_icon_button(url, _("Archive this event"), "delete")
        else:
            return ''

    def paint_event_icons(row, history=False):
        htmlcode = render_event_phase_icons(row)

        if not history:
            htmlcode += render_delete_event_icons(row)

        if htmlcode:
            return "icons", htmlcode
        else:
            return "", ""

    multisite_painters["event_icons"] = {
        "title"   : _("Event Icons"),
        "short"   : _("Icons"),
        "printable" : False,
        "columns" : [ "event_phase" ],
        "paint"   : paint_event_icons,
    }


    multisite_painters["event_history_icons"] = {
        "title"   : _("Event Icons"),
        "short"   : _("Icons"),
        "printable" : False,
        "columns" : [ "event_phase" ],
        "paint"   : lambda row: paint_event_icons(row, history=True),
    }


    def paint_event_contact_groups(row):
        cgs = row.get("event_contact_groups")
        if cgs == None:
            return "", ""
        elif cgs:
            return "", ", ".join(cgs)
        else:
            return "", "<i>"  + _("none") + "</i>"

    multisite_painters["event_contact_groups"] = {
        "title"   : _("Contact groups defined in rule"),
        "short"   : _("Rule Contact Groups"),
        "columns" : [ "event_contact_groups" ],
        "paint"   : paint_event_contact_groups,
    }

    # Event History

    multisite_painters["history_line"] = {
        "title"   : _("Line number in log file"),
        "short"   : _("Line"),
        "columns" : ["history_line" ],
        "paint"   : lambda row: ("number", "%s" % row["history_line"]),
    }

    multisite_painters["history_time"] = {
        "title"   : _("Time of entry in logfile"),
        "short"   : _("Time"),
        "columns" : ["history_time" ],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["history_time"], True, True),
    }

    def paint_ec_history_what(row):
        what = row["history_what"]
        return "", '<span title="%s">%s</span>' % (mkeventd.action_whats[what], what)

    multisite_painters["history_what"] = {
        "title"   : _("Type of event action"),
        "short"   : _("Action"),
        "columns" : ["history_what" ],
        "paint"   : paint_ec_history_what,
    }

    multisite_painters["history_what_explained"] = {
        "title"   : _("Explanation for event action"),
        "columns" : ["history_what" ],
        "paint"   : lambda row: ("", mkeventd.action_whats[row["history_what"]]),
    }


    multisite_painters["history_who"] = {
        "title"   : _("User who performed action"),
        "short"   : _("Who"),
        "columns" : ["history_who" ],
        "paint"   : lambda row: ("", row["history_who"]),
    }

    multisite_painters["history_addinfo"] = {
        "title"   : _("Additional Information"),
        "short"   : _("Info"),
        "columns" : ["history_addinfo" ],
        "paint"   : lambda row: ("", row["history_addinfo"]),
    }

    #.
    #   .--Commands------------------------------------------------------------.
    #   |         ____                                          _              |
    #   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
    #   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
    #   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
    #   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    def command_executor_mkeventd(command, site):
        mkeventd.execute_command(command, site=site)

    # Acknowledge and update comment and contact
    config.declare_permission("mkeventd.update",
            _("Update an event"),
            _("Needed for acknowledging and changing the comment and contact of an event"),
            [ "user", "admin" ])

    # Sub-Permissions for Changing Comment, Contact and Acknowledgement
    config.declare_permission("mkeventd.update_comment",
            _("Update an event: change comment"),
            _("Needed for changing a comment when updating an event"),
            [ "user", "admin" ])
    config.declare_permission("mkeventd.update_contact",
            _("Update an event: change contact"),
            _("Needed for changing a contact when updating an event"),
            [ "user", "admin" ])

    def render_mkeventd_update():
        html.open_table(border=0, cellpadding=0, cellspacing=3)
        if config.user.may("mkeventd.update_comment"):
            html.open_tr()
            html.open_td()
            html.write(_("Change comment:"))
            html.close_td()
            html.open_td()
            html.text_input('_mkeventd_comment', size=50)
            html.close_td()
            html.close_tr()
        if config.user.may("mkeventd.update_contact"):
            html.open_tr()
            html.open_td()
            html.write(_("Change contact:"))
            html.close_td()
            html.open_td()
            html.text_input('_mkeventd_contact', size=50)
            html.close_td()
            html.close_tr()
        html.open_tr()
        html.td('')
        html.open_td()
        html.checkbox('_mkeventd_acknowledge', True, label=_("Set event to acknowledged"))
        html.close_td()
        html.close_tr()
        html.close_table()
        html.button('_mkeventd_update', _("Update"))

    def command_mkeventd_update(cmdtag, spec, row):
        if html.var('_mkeventd_update'):
            if config.user.may("mkeventd.update_comment"):
                comment = html.get_unicode_input("_mkeventd_comment").strip().replace(";",",")
            else:
                comment = ""
            if config.user.may("mkeventd.update_contact"):
                contact = html.get_unicode_input("_mkeventd_contact").strip().replace(":",",")
            else:
                contact = ""
            ack = html.get_checkbox("_mkeventd_acknowledge")
            return "UPDATE;%s;%s;%s;%s;%s" % \
                (row["event_id"], config.user.id, ack and 1 or 0, comment, contact), \
                _("update")

    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.update",
        "title"       : _("Update &amp; Acknowledge"),
        "render"      : render_mkeventd_update,
        "action"      : command_mkeventd_update,
        "executor"    : command_executor_mkeventd,
    })

    # Change event state
    config.declare_permission("mkeventd.changestate",
            _("Change event state"),
            _("This permission allows to change the state classification of an event "
              "(e.g. from CRIT to WARN)."),
            [ "user", "admin" ])

    def render_mkeventd_changestate():
        html.button('_mkeventd_changestate', _("Change Event state to:"))
        html.nbsp()
        MonitoringState().render_input("_mkeventd_state", 2)

    def command_mkeventd_changestate(cmdtag, spec, row):
        if html.var('_mkeventd_changestate'):
            state = MonitoringState().from_html_vars("_mkeventd_state")
            return "CHANGESTATE;%s;%s;%s" % \
                (row["event_id"], config.user.id, state), \
                _("change the state")

    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.changestate",
        "title"       : _("Change State"),
        "render"      : render_mkeventd_changestate,
        "action"      : command_mkeventd_changestate,
        "executor"    : command_executor_mkeventd,
    })


    # Perform custom actions
    config.declare_permission("mkeventd.actions",
            _("Perform custom action"),
            _("This permission is needed for performing the configured actions "
              "(execution of scripts and sending emails)."),
            [ "user", "admin" ])

    def render_mkeventd_actions():
        for action_id, title in mkeventd.action_choices(omit_hidden = True):
            html.button("_action_" + action_id, title)
            html.br()

    def command_mkeventd_action(cmdtag, spec, row):
        for action_id, title in mkeventd.action_choices(omit_hidden = True):
            if html.var("_action_" + action_id):
                return "ACTION;%s;%s;%s" % (row["event_id"], config.user.id, action_id), \
                  (_("execute the action \"%s\"") % title)

    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.actions",
        "title"       : _("Custom Action"),
        "render"      : render_mkeventd_actions,
        "action"      : command_mkeventd_action,
        "executor"    : command_executor_mkeventd,
    })


    # Delete events
    config.declare_permission("mkeventd.delete",
            _("Archive an event"),
            _("Finally archive an event without any further action"),
            [ "user", "admin" ])


    def command_mkeventd_delete(cmdtag, spec, row):
        if html.var("_delete_event"):
            command = "DELETE;%s;%s" % (row["event_id"], config.user.id)
            title = _("<b>archive</b>")
            return command, title


    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.delete",
        "title"       : _("Archive Event"),
        "render"      : lambda: \
            html.button("_delete_event", _("Archive Event")),
        "action"      : command_mkeventd_delete,
        "executor"    : command_executor_mkeventd,
    })


    config.declare_permission("mkeventd.archive_events_of_hosts",
                              _("Archive events of hosts"),
                              _("Archive all open events of all hosts shown in host views"),
                              [ "user", "admin" ])


    def command_archive_events_of_hosts(cmdtag, spec, row):
        if html.var("_archive_events_of_hosts"):
            if cmdtag == "HOST":
                tag = "host"
            elif cmdtag == "SVC":
                tag = "service"
            else:
                tag = None

            commands = []
            if tag and row.get('%s_check_command' % tag, "").startswith('check_mk_active-mkevents'):
                data = sites.live().query("GET eventconsoleevents\n" +\
                                          "Columns: event_id\n" +\
                                          "Filter: host_name = %s" % \
                                          row['host_name'])
                commands = [ "DELETE;%s;%s" % (entry[0], config.user.id) for entry in data ]
            return commands, "<b>archive all events of all hosts</b> of"


    multisite_commands.append({
        "tables"     : [ "host", "service" ],
        "permission" : "mkeventd.archive_events_of_hosts",
        "title"      : _("Archive events of hosts"),
        "render"     : lambda: html.button("_archive_events_of_hosts", _('Archive events')),
        "action"     : command_archive_events_of_hosts,
        "executor"   : command_executor_mkeventd,
    })


    #.
    #   .--Sorters-------------------------------------------------------------.
    #   |                  ____             _                                  |
    #   |                 / ___|  ___  _ __| |_ ___ _ __ ___                   |
    #   |                 \___ \ / _ \| '__| __/ _ \ '__/ __|                  |
    #   |                  ___) | (_) | |  | ||  __/ |  \__ \                  |
    #   |                 |____/ \___/|_|   \__\___|_|  |___/                  |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    def cmp_simple_state(column, ra, rb):
        a = ra.get(column, -1)
        b = rb.get(column, -1)
        if a == 3:
            a = 1.5
        if b == 3:
            b = 1.5
        return cmp(a, b)


    declare_1to1_sorter("event_id",          cmp_simple_number)
    declare_1to1_sorter("event_count",       cmp_simple_number)
    declare_1to1_sorter("event_text",        cmp_simple_string)
    declare_1to1_sorter("event_first",       cmp_simple_number)
    declare_1to1_sorter("event_last",        cmp_simple_number)
    declare_1to1_sorter("event_comment",     cmp_simple_string)
    declare_1to1_sorter("event_sl",          cmp_simple_number)
    declare_1to1_sorter("event_host",        cmp_num_split)
    declare_1to1_sorter("event_ipaddress",   cmp_num_split)
    declare_1to1_sorter("event_contact",     cmp_simple_string)
    declare_1to1_sorter("event_application", cmp_simple_string)
    declare_1to1_sorter("event_pid",         cmp_simple_number)
    declare_1to1_sorter("event_priority",    cmp_simple_number)
    declare_1to1_sorter("event_facility",    cmp_simple_number) # maybe convert to text
    declare_1to1_sorter("event_rule_id",     cmp_simple_string)
    declare_1to1_sorter("event_state",       cmp_simple_state)
    declare_1to1_sorter("event_phase",       cmp_simple_string)
    declare_1to1_sorter("event_owner",       cmp_simple_string)

    declare_1to1_sorter("history_line",      cmp_simple_number)
    declare_1to1_sorter("history_time",      cmp_simple_number)
    declare_1to1_sorter("history_what",      cmp_simple_string)
    declare_1to1_sorter("history_who",       cmp_simple_string)
    declare_1to1_sorter("history_addinfo",   cmp_simple_string)

    #.
    #   .--Views---------------------------------------------------------------.
    #   |                    __     ___                                        |
    #   |                    \ \   / (_) _____      _____                      |
    #   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
    #   |                      \ V / | |  __/\ V  V /\__ \                     |
    #   |                       \_/  |_|\___| \_/\_/ |___/                     |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    def mkeventd_view(d):
        x = {
            'topic':           _('Event Console'),
            'browser_reload':  60,
            'column_headers':  'pergroup',
            'icon':            'mkeventd',
            'mobile':          False,
            'hidden':          False,
            'mustsearch':      False,
            'group_painters':  [],
            'num_columns':     1,
            'hidebutton':      False,
            'play_sounds':     False,
            'public':          True,
            'sorters':         [],
            'user_sortable':   'on',
            'show_filters':    [],
            'hard_filters':    [],
            'hide_filters':    [],
            'hard_filtervars': [],
        }
        x.update(d)
        return x

    # Table of all open events
    multisite_builtin_views['ec_events'] = mkeventd_view({
        'title':       _('Events'),
        'description': _('Table of all currently open events (handled and unhandled)'),
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_host',   'ec_events_of_host', ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_host_regex',
            'event_ipaddress',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'event_sl_max',
            'hostregex',
            'siteopt',
        ],
        'hard_filtervars': [
            ( 'event_phase_open',     "on" ),
            ( 'event_phase_ack',      "on" ),
            ( 'event_phase_counting', ""   ),
            ( 'event_phase_delayed',  ""   ),
        ],
        'sorters': [
            ('event_last', False)
        ],
    })

    multisite_builtin_views['ec_events_of_monhost'] = mkeventd_view({
        'title':       _('Events of Monitored Host'),
        'description': _('Currently open events of a host that is monitored'),
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'hidden':      True,
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'event_sl_max',
        ],
        'hide_filters': [
            'siteopt',
            'host',
        ],
        'sorters': [
            ('event_last', False)
        ],
    })
    multisite_builtin_views['ec_events_of_host'] = mkeventd_view({
        'title':       _('Events of Host'),
        'description': _('Currently open events of one specific host'),
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'hidden':      True,
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'event_sl_max',
        ],
        'hide_filters': [
            'siteopt',
            'event_host',
        ],
        'sorters': [
            ('event_last', False)
        ],
    })

    multisite_builtin_views['ec_event'] = mkeventd_view({
        'title':        _('Event Details'),
        'description':  _('Details about one event'),
        'linktitle':    'Event Details',
        'datasource':   'mkeventd_events',
        'layout':       'dataset',

        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
        ],
        'painters': [
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('event_ipaddress', None, ''),
            ('foobar', None, ''),
            ('alias', 'hoststatus', ''),
            ('host_contacts', None, ''),
            ('host_icons', None, ''),
            ('event_text', None, ''),
            ('event_match_groups', None, ''),
            ('event_comment', None, ''),
            ('event_owner', None, ''),
            ('event_first', None, ''),
            ('event_last', None, ''),
            ('event_id', None, ''),
            ('event_icons', None, ''),
            ('event_count', None, ''),
            ('event_sl', None, ''),
            ('event_contact', None, ''),
            ('event_contact_groups', None, ''),
            ('event_application', None, ''),
            ('event_pid', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_rule_id', None, ''),
            ('event_phase', None, ''),
            ('host_services', None, ''),
        ],
    })

    multisite_builtin_views['ec_history_recent'] = mkeventd_view({
        'title':       _('Recent Event History'),
        'description': _('Information about events and actions on events during the recent 24 hours.'),
        'datasource':  'mkeventd_history',
        'layout':      'table',

        'painters': [
            ('history_time', None, ''),
            ('event_id',     'ec_historyentry', ''),
            ('history_who',  None, ''),
            ('history_what', None, ''),
            ('event_history_icons', None, ''),
            ('event_state',   None, ''),
            ('event_phase',   None, ''),
            ('event_sl',      None, ''),
            ('event_host',   'ec_history_of_host', ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_host_regex',
            'event_ipaddress',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'event_sl_max',
            'history_time',
            'history_who',
            'history_what',
            'host_state_type',
            'hostregex',
            'siteopt',
        ],
        'hard_filtervars': [
           ('history_time_from', '1'),
           ('history_time_from_range', '86400'),
        ],
        'sorters': [
            ('history_time', True),
            ('history_line', True),
        ],
    })

    multisite_builtin_views['ec_historyentry'] = mkeventd_view({
        'title':        _('Event History Entry'),
        'description':  _('Details about a historical event history entry'),
        'datasource':   'mkeventd_history',
        'layout':       'dataset',

        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
            'history_line',
        ],
        'painters': [
            ('history_time', None, ''),
            ('history_line', None, ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('history_addinfo', None, ''),
            ('event_state', None, ''),
            ('event_host', 'ec_history_of_host', ''),
            ('event_ipaddress', None, ''),
            ('event_text', None, ''),
            ('event_match_groups', None, ''),
            ('event_comment', None, ''),
            ('event_owner', None, ''),
            ('event_first', None, ''),
            ('event_last', None, ''),
            ('event_id', 'ec_history_of_event', ''),
            ('event_history_icons', None, ''),
            ('event_count', None, ''),
            ('event_sl', None, ''),
            ('event_contact', None, ''),
            ('event_contact_groups', None, ''),
            ('event_application', None, ''),
            ('event_pid', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_rule_id', None, ''),
            ('event_phase', None, ''),
        ],
    })

    multisite_builtin_views['ec_history_of_event'] = mkeventd_view({
        'title':        _('History of Event'),
        'description':  _('History entries of one specific event'),
        'datasource':   'mkeventd_history',
        'layout':       'table',
        'columns':      1,

        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
        ],
        'painters': [
            ('history_time', None, ''),
            ('history_line', 'ec_historyentry', ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('event_application', None, ''),
            ('event_text', None, ''),
            ('event_sl', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_phase', None, ''),
            ('event_count', None, ''),
        ],
        'sorters': [
            ('history_time', True),
            ('history_line', True),
        ],
    })

    multisite_builtin_views['ec_history_of_host'] = mkeventd_view({
        'title':        _('Event History of Host'),
        'description':  _('History entries of one specific host'),
        'datasource':   'mkeventd_history',
        'layout':       'table',
        'columns':      1,

        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_host',
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'event_sl_max',
            'history_time',
            'history_who',
            'history_what',
        ],
        'painters': [
            ('history_time', None, ''),
            ('event_id', 'ec_history_of_event', ''),
            ('history_line', 'ec_historyentry', ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('event_ipaddress', None, ''),
            ('event_application', None, ''),
            ('event_text', None, ''),
            ('event_sl', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_phase', None, ''),
            ('event_count', None, ''),
        ],
        'sorters': [
            ('history_time', True),
            ('history_line', True),
        ],
    })

    multisite_builtin_views['ec_event_mobile'] = \
         {'browser_reload': 0,
          'column_headers': 'pergroup',
          'context': {},
          'datasource': 'mkeventd_events',
          'description': u'Details about one event\n',
          'group_painters': [],
          'hidden': True,
          'hidebutton': False,
          'icon': 'mkeventd',
          'layout': 'mobiledataset',
          'linktitle': u'Event Details',
          'mobile': True,
          'name': 'ec_event_mobile',
          'num_columns': 1,
          'painters': [('event_state', None, None),
                       ('event_host', None, None),
                       ('event_ipaddress', None, ''),
                       ('host_address', 'hoststatus', None),
                       ('host_contacts', None, None),
                       ('host_icons', None, None),
                       ('event_text', None, None),
                       ('event_comment', None, None),
                       ('event_owner', None, None),
                       ('event_first', None, None),
                       ('event_last', None, None),
                       ('event_id', None, None),
                       ('event_icons', None, None),
                       ('event_count', None, None),
                       ('event_sl', None, None),
                       ('event_contact', None, None),
                       ('event_contact_groups', None, None),
                       ('event_application', None, None),
                       ('event_pid', None, None),
                       ('event_priority', None, None),
                       ('event_facility', None, None),
                       ('event_rule_id', None, None),
                       ('event_phase', None, None),
                       ('host_services', None, None)],
          'public': True,
          'single_infos': ['event'],
          'sorters': [],
          'title': u'Event Details',
          'topic': u'Event Console',
          'user_sortable': True}

    multisite_builtin_views['ec_events_mobile'] = \
          {'browser_reload': 60,
           'column_headers': 'pergroup',
           'context': {'event_application': {'event_application': ''},
                       'event_comment': {'event_comment': ''},
                       'event_contact': {'event_contact': ''},
                       'event_count': {'event_count_from': '',
                                       'event_count_to': ''},
                       'event_facility': {'event_facility': ''},
                       'event_first': {'event_first_from': '',
                                       'event_first_from_range': '3600',
                                       'event_first_until': '',
                                       'event_first_until_range': '3600'},
                       'event_host_regex': {'event_host_regex': ''},
                       'event_id': {'event_id': ''},
                       'event_last': {'event_last_from': '',
                                      'event_last_from_range': '3600',
                                      'event_last_until': '',
                                      'event_last_until_range': '3600'},
                       'event_phase': {'event_phase_ack': 'on',
                                       'event_phase_closed': 'on',
                                       'event_phase_counting': '',
                                       'event_phase_delayed': '',
                                       'event_phase_open': 'on'},
                       'event_priority': {'event_priority_0': 'on',
                                          'event_priority_1': 'on',
                                          'event_priority_2': 'on',
                                          'event_priority_3': 'on',
                                          'event_priority_4': 'on',
                                          'event_priority_5': 'on',
                                          'event_priority_6': 'on',
                                          'event_priority_7': 'on'},
                       'event_rule_id': {'event_rule_id': ''},
                       'event_sl': {'event_sl': ''},
                       'event_sl_max': {'event_sl_max': ''},
                       'event_state': {'event_state_0': 'on',
                                       'event_state_1': 'on',
                                       'event_state_2': 'on',
                                       'event_state_3': 'on'},
                       'event_text': {'event_text': ''},
                       'hostregex': {'host_regex': ''}},
           'datasource': 'mkeventd_events',
           'description': u'Table of all currently open events (handled and unhandled)\n',
           'group_painters': [],
           'hidden': False,
           'hidebutton': False,
           'icon': 'mkeventd',
           'layout': 'mobilelist',
           'linktitle': u'Events',
           'mobile': True,
           'name': 'ec_events_mobile',
           'num_columns': 1,
           'owner': 'cmkadmin',
           'painters': [('event_id', 'ec_event_mobile', None),
                        ('event_state', None, None),
                        ('event_host', 'ec_events_of_host', None),
                        ('event_application', None, None),
                        ('event_text', None, None),
                        ('event_last', None, None)],
           'public': True,
           'single_infos': [],
           'sorters': [
               ('event_last', False)
           ],
           'title': u'Events',
           'topic': u'Event Console',
           'user_sortable': True}
