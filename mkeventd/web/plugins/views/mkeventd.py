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

import mkeventd
from  valuespec import *

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

def table_events(what, columns, add_headers, only_sites, limit, filters):
    # First we fetch the list of all events from mkeventd - either current
    # or historic ones. We ignore any filters for host_ here. Note:
    # event_host and host_name needn't be compatible. They might differ
    # in case. Also in the events table instead of the host name there
    # might be the IP address of the host - while in the monitoring we
    # name. We will join later.

    # If due to limitation of visibility we do a post-filtering, we cannot
    # impose a limit when fetching the data. This is dangerous, but we
    # have no other chance, currently.
    if not config.may("mkeventd.seeall"):
        use_limit = None
    else:
        use_limit = limit
    rows = get_all_events(what, filters, use_limit)

    # Now we join the stuff with the host information. Therefore we
    # get the information about all hosts that are referred to in
    # any of the events.
    required_hosts = set()
    for row in rows:
        host = row.get("event_host")
        if host:
            required_hosts.add(host.lower())

    # Get information about these hosts via Livestatus. We
    # allow event_host to match either the host_name or
    # the host_address.
    host_filters = ""
    for host in required_hosts:
        host_filters += "Filter: host_name =~ %s\n" \
                        "Filter: host_address = %s\n" % (host.encode("utf-8"), host.encode("utf-8"))
    if len(required_hosts) > 0:
        host_filters += "Or: %d\n" % (len(required_hosts) * 2)

    # Make sure that the host name is fetched. We need it for
    # joining. The event columns are always fetched all. The event
    # daemon currently does not implement any Columns: header.
    if "host_name" not in columns:
        columns.append("host_name")
    if "host_address" not in columns:
        columns.append("host_address")

    # Fetch list of hosts. Here is much room for optimization.
    # If no host filter is set, then the data of all hosts would
    # be fetched before we even know if there are any events
    # for those hosts. Better would be first fetching all events
    # and later fetch the data of the relevant hosts.
    hostrows = event_hostrows(columns, only_sites, filters, host_filters)

    # Sichtbarkeit: Wenn der Benutzer *nicht* das Recht hat, alle Events
    # zu sehen, dann müssen wir die Abfrage zweimal machen. Einmal with
    # AuthUser: (normal) und einmal zusätzlich ohne AuthUser. Dabei brauchen
    # wir dann nicht mehr alle Spalten, sondern nur noch die Liste der
    # Kontaktgruppen.
    # 1. Wenn ein Host bei der ersten Anfrage fehlt, aber bei der zweiten kommt,
    # heißt das, dass der User diesen Host nicht sehen darf. Und der Event wird
    # nicht angezeigt.
    # 2. Wenn ein Host bei beiden Abfragen fehlt, gibt es diesen Host nicht im
    # Monitoring. Dann gibt es zwei Fälle:
    # a) Wenn im Event eine Liste von Kontaktgruppen eingetragen ist (kommt durch
    # eine Regel), dann darf der User den Event sehen, wenn er Mitglied einer
    # der Kontaktgruppen ist. Dies bekommen wir einfach aus dem User-Profil
    # heraus. Für solche Events brauchen wir das Ergebnis der Abfrage nicht.
    # b) Wenn im Event diese Option fehlt, dann darf der User das Event immer sehen.
    # Wir können das aber nochmal global steuern über eine Permission.

    if not config.may("mkeventd.seeall"):
        host_contact_groups = {}
        query = "GET hosts\nColumns: name address contact_groups\n" + host_filters
        html.live.set_only_sites(only_sites)
        html.live.set_auth_domain('mkeventd')
        data = html.live.query(query)
        html.live.set_auth_domain('read')
        html.live.set_only_sites(None)
        for host, address, groups in data:
            host_contact_groups[host.lower()] = groups
            host_contact_groups[address] = groups

    else:
        host_contact_groups = None

    # Create lookup dict from hostname/address to the dataset of the host.
    # This speeds up the mapping to the events.
    hostdict = {}
    for row in hostrows:
        hostdict[row["host_name"].lower()] = row
        hostdict[row["host_address"]] = row

    # If there is at least one host filter, then we do not show event
    # entries with an empty host information
    have_host_filter = False
    for filt in filters:
        if filt.info == "host":
            filter_code = filt.filter('event')
            if filter_code:
                have_host_filter = True
                break

    if not have_host_filter:
        # Create empty host for outer join on host table
        empty_host = dict([ (c, "") for c in columns if c.startswith("host_") ])
        empty_host["site"] = ''
        empty_host["host_state"] = 0
        empty_host["host_has_been_checked"] = 0

    # We're ready to join the host-data with the event data now. The question
    # is what to do with events that cannot be mapped to a host...
    new_rows = []
    user_contact_groups = None
    for event in rows:
        host = event["event_host"].lower()

        # Users without the mkeventd.seeall permission only may see the host if
        # they are a contact via the monitoring. In case the host is not known
        # to the monitoring the permission mkeventd.seeunrelated is being neccessary
        # as well.
        if host_contact_groups != None:
            if host in host_contact_groups:
                if host not in hostdict:
                    continue # Host known to monitoring, but user is now allowed
            else: # Host not known to monitoring
                # Has the event explicit contact groups assigned? Use them!
                cgs = event.get("event_contact_groups")
                if cgs == None:
                    if not config.may("mkeventd.seeunrelated"):
                        continue
                else:
                    if user_contact_groups == None:
                        user_contact_groups = get_user_contact_groups()

                    allowed = False
                    for g in cgs:
                        if g in user_contact_groups:
                            allowed = True
                    if not allowed:
                        continue

        if host in hostdict:
            event.update(hostdict[host])
            new_rows.append(event)
        elif not have_host_filter:
            # This event does not belong to any host known by
            # the monitoring. We need to create the columns nevertheless.
            # TODO: If there are any host filters, these events should
            # be dropped.
            # Hier könnten wir Leerdaten eintragen. Dann
            # kann man auch Events sehen, die keinem
            # Host zugeordnet sind. Wenn wir nichts machen,
            # dann fehlen Spalten und die Painter fallen
            # auf die Nase.
            event.update(empty_host)
            new_rows.append(event)

    return new_rows


def event_hostrows(columns, only_sites, filters, host_filters):
    filter_code = ""
    for filt in filters:
        header = filt.filter("event")
        if not header.startswith("Sites:"):
            filter_code += header
    filter_code += host_filters

    host_columns = filter(lambda c: c.startswith("host_"), columns)
    return get_host_table(filter_code, only_sites, host_columns)


def get_user_contact_groups():
    query = "GET contactgroups\nFilter: members >= %s\nColumns: name\nCache: reload" % (config.user_id)
    contacts = html.live.query_column(query)
    return set(contacts)

def get_host_table(filter_header, only_sites, add_columns):
    columns = [ "host_name" ] + add_columns

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)
    data = html.live.query(
            "GET hosts\n" +
            "Columns: " + (" ".join(columns)) + "\n" +
            filter_header)
    html.live.set_prepend_site(False)
    html.live.set_only_sites(None)

    headers = [ "site" ] + columns
    rows = [ dict(zip(headers, row)) for row in data ]
    return rows

def get_all_events(what, filters, limit):
    headers = ""
    for f in filters:
        try:
            headers += f.event_headers()
        except:
            pass
    if limit:
        headers += "Limit: %d\n" % limit

    query = "GET %s\n%s" % (what, headers)
    try:
        debug = config.debug_mkeventd_queries
    except:
        debug = False
    if debug \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message" onmouseover="this.style.display=\'none\';">'
                   '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))
    response = mkeventd.query(query)

    # First line of the response is the list of column names.
    headers = response[0]
    rows = []
    for r in response[1:]:
        rows.append(dict(zip(headers, r)))
    return rows


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
             "controls wether he/she can see events that are not related to a host in the montioring "
             "and that do not have been assigned specific contract groups to via the event rule."),
           [ "user", "admin", "guest" ])

    multisite_datasources["mkeventd_events"] = {
        "title"       : _("Event Console: Current Events"),
        "table"       : lambda *args: table_events('events', *args),
        "infos"       : [ "event", "host" ],
        "keys"        : [],
        "idkeys"      : [ 'site', 'host_name', 'event_id' ],
        "time_filters" : [ "event_first" ],
    }

    multisite_datasources["mkeventd_history"] = {
        "title"       : _("Event Console: Event History"),
        "table"       : lambda *args: table_events('history', *args),
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
        if config.may("mkeventd.edit"):
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
        name = nagios_short_state_names[row["event_state"]]
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

    def paint_event_icons(row):
        phase = row["event_phase"]
        if phase == "ack":
            title = _("This event has been acknowledged.")
        elif phase == "counting":
            title = _("This event has not reached the target count yet.")
        elif phase == "delayed":
            title = _("The action of this event is still delayed in the hope of a cancelling event.")
        else:
            return "", ""
        return 'icons', '<img class=icon title="%s" src="images/icon_%s.png">' % (title, phase)

    multisite_painters["event_icons"] = {
        "title"   : _("Event Icons"),
        "short"   : _("Icons"),
        "printable" : False,
        "columns" : [ "event_phase" ],
        "paint"   : paint_event_icons,
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
        "title"   : _("Fallback Contact Groups"),
        "short"   : _("Contact Groups"),
        "columns" : [ "event_contact_groups" ],
        "paint"   : paint_event_contact_groups,
    }

    # Event History

    multisite_painters["history_line"] = {
        "title"   : _("Line number in log file"),
        "short"   : _("Line"),
        "columns" : ["history_line" ],
        "paint"   : lambda row: ("number", row["history_line"]),
    }

    multisite_painters["history_time"] = {
        "title"   : _("Time of entry in logfile"),
        "short"   : _("Time"),
        "columns" : ["history_time" ],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["history_time"], True, True),
    }

    multisite_painters["history_what"] = {
        "title"   : _("Type of event action"),
        "short"   : _("Action"),
        "columns" : ["history_what" ],
        "paint"   : lambda row: ("", row["history_what"]),
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
        response = mkeventd.query("COMMAND %s" % command)


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
        html.write('<table border=0 cellspacing=3 cellpadding=0>')
        if config.may("mkeventd.update_comment"):
            html.write('<tr><td>%s</td><td>' % _("Change comment:"))
            html.text_input('_mkeventd_comment', size=50)
            html.write('</td></tr>')
        if config.may("mkeventd.update_contact"):
            html.write('<tr><td>%s</td><td>' % _("Change contact:"))
            html.text_input('_mkeventd_contact', size=50)
            html.write('</td></tr>')
        html.write('<td></td><td>')
        html.checkbox('_mkeventd_acknowledge', True, label=_("Set event to acknowledged"))
        html.write('</td></tr>')
        html.write('</table>')
        html.button('_mkeventd_update', _("Update"))

    def command_mkeventd_update(cmdtag, spec, row):
        if html.var('_mkeventd_update'):
            if config.may("mkeventd.update_comment"):
                comment = html.var_utf8("_mkeventd_comment").strip().replace(";",",")
            else:
                comment = ""
            if config.may("mkeventd.update_contact"):
                contact = html.var_utf8("_mkeventd_contact").strip().replace(":",",")
            else:
                contact = ""
            ack = html.get_checkbox("_mkeventd_acknowledge")
            return "UPDATE;%s;%s;%s;%s;%s" % \
                (row["event_id"], config.user_id, ack and 1 or 0, comment, contact), \
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
        html.write("&nbsp;")
        MonitoringState().render_input("_mkeventd_state", 2)

    def command_mkeventd_changestate(cmdtag, spec, row):
        if html.var('_mkeventd_changestate'):
            state = MonitoringState().from_html_vars("_mkeventd_state")
            return "CHANGESTATE;%s;%s;%s" % \
                (row["event_id"], config.user_id, state), \
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
            html.write("<br>")

    def command_mkeventd_action(cmdtag, spec, row):
        for action_id, title in mkeventd.action_choices(omit_hidden = True):
            if html.var("_action_" + action_id):
                return "ACTION;%s;%s;%s" % (row["event_id"], config.user_id, action_id), \
                  (_("execute that action &quot;%s&quot") % title)

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
            command = "DELETE;%s;%s" % (row["event_id"], config.user_id)
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
        ],
        'hard_filtervars': [
            ( 'event_phase_open',     "on" ),
            ( 'event_phase_ack',      "on" ),
            ( 'event_phase_counting', ""   ),
            ( 'event_phase_delayed',  ""   ),
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
            ('host_address', 'hoststatus', ''),
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
            ('event_icons', None, ''),
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
           'owner': 'omdadmin',
           'painters': [('event_id', 'ec_event_mobile', None),
                        ('event_state', None, None),
                        ('event_host', 'ec_events_of_host', None),
                        ('event_application', None, None),
                        ('event_text', None, None),
                        ('event_last', None, None)],
           'public': True,
           'single_infos': [],
           'sorters': [],
           'title': u'Events',
           'topic': u'Event Console',
           'user_sortable': True}
