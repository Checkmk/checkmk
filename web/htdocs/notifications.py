#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

import config
import lib
import errno
import os
import sites
import table
import time
import wato


g_acknowledgement_time = {}
g_modified_time        = 0
g_columns              = ["time", "contact_name", "type", "host_name",
                          "service_description", "comment"]
loaded_with_language   = False


def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == current_language and not force:
        return

    config.declare_permission_section("notification_plugin",
                                      _("Notification plugins"),
                                      do_sort = True)

    for name, attrs in wato.load_notification_scripts().items():
        config.declare_permission(
            "notification_plugin.%s" % name,
            _u(attrs["title"]), u"",
            [ "admin", "user" ])

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language


def acknowledge_failed_notifications(timestamp):
    g_acknowledgement_time[config.user.id] = timestamp
    save_acknowledgements()

def set_modified_time():
    global g_modified_time
    g_modified_time = time.time()

def save_acknowledgements():
    config.user.save_file("acknowledged_notifications", int(g_acknowledgement_time[config.user.id]))
    set_modified_time()

def acknowledged_time():
    if g_acknowledgement_time.get(config.user.id) is None or\
            config.user.file_modified("acknowledged_notifications") > g_modified_time:
        load_acknowledgements()
    return g_acknowledgement_time[config.user.id]

def load_acknowledgements():
    g_acknowledgement_time[config.user.id] = config.user.load_file("acknowledged_notifications", 0)
    set_modified_time()
    if g_acknowledgement_time[config.user.id] == 0:
        # when this timestamp is first initialized, save the current timestamp as the acknowledge
        # date. This should considerably reduce the number of log files that have to be searched
        # when retrieving the list
        acknowledge_failed_notifications(time.time())

def load_failed_notifications(before=None, after=None, stat_only=False, extra_headers=None):
    may_see_notifications =\
        config.user.may("general.see_failed_notifications") or\
        config.user.may("general.see_failed_notifications_24h")

    if not may_see_notifications:
        return [0]

    query_filters = [
        "class = 3",
        "log_type = SERVICE NOTIFICATION RESULT",
    ]

    if before is not None:
        query_filters.append("time <= %d" % before)
    if after is not None:
        query_filters.append("time >= %d" % after)
    if may_see_notifications and not config.user.may("general.see_failed_notifications"):
        query_filters.append("time > %d" % (int(time.time()) - 86400))

    query = ["GET log"]
    if stat_only:
        query.append("Stats: log_state != 0")
    else:
        query.append("Columns: %s" % " ".join(g_columns))
        query_filters.append("log_state != 0")
    query += ["Filter: %s" % filt for filt in query_filters]

    query = "\n".join(query)

    if extra_headers is not None:
        query += extra_headers

    if stat_only:
        result = sites.live().query_summed_stats(query)
        if result is None:
            result = [0] # Normalize the result when no site answered

        if result[0] == 0 and not sites.live().dead_sites():
            # In case there are no errors and all sites are reachable:
            # advance the users acknowledgement time
            acknowledge_failed_notifications(time.time())

        return result

    else:
        return sites.live().query(query)

def render_notification_table(failed_notifications):
    table.begin()

    header = dict([(name, idx) for idx, name in enumerate(g_columns)])

    for row in failed_notifications:
        table.row()
        table.cell(_("Time"),    lib.age_human_readable(time.time() - row[header['time']]))
        table.cell(_("Contact"), row[header['contact_name']])
        table.cell(_("Plugin"),  row[header['type']])
        table.cell(_("Host"),    row[header['host_name']])
        table.cell(_("Service"), row[header['service_description']])
        table.cell(_("Output"),  row[header['comment']])

    table.end()

# TODO: We should really recode this to use the view and a normal view command / action
def render_page_confirm(acktime, prev_url, failed_notifications):
    html.header(_("Confirm failed notifications"), javascripts=[], stylesheets=[ "pages", "check_mk" ])

    if failed_notifications:
        html.write('<div class="really">\n')
        html.write(_("Do you really want to acknowledge all failed notifications up to %s?") %\
                   lib.datetime_human_readable(acktime))
        html.begin_form("confirm", method="GET", action=prev_url)
        html.hidden_field('acktime', acktime),
        html.button('_confirm', _("Yes"))
        html.end_form()
        html.write('</div>\n')

    render_notification_table(failed_notifications)

    html.footer()

def page_clear():
    acktime = html.var('acktime')
    if acktime is None:
        acktime = time.time()
    else:
        acktime = float(acktime)

    prev_url = html.var('prev_url')
    if html.var('_confirm'):
        acknowledge_failed_notifications(acktime)
        html.reload_sidebar()

        if config.user.authorized_login_sites():
            wato.user_profile_async_replication_page()
            return

    failed_notifications = load_failed_notifications(before=acktime,
                                                     after=acknowledged_time())
    render_page_confirm(acktime, prev_url, failed_notifications)

