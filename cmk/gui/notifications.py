#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from livestatus import MKLivestatusNotFoundError
import cmk.utils.render

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.table import table_element
import cmk.gui.watolib as watolib
import cmk.gui.i18n
import cmk.gui.pages
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    declare_permission,
)

g_acknowledgement_time = {}
g_modified_time = 0.0
g_columns = ["time", "contact_name", "type", "host_name", "service_description", "comment"]


@permission_section_registry.register
class PermissionSectionNotificationPlugins(PermissionSection):
    @property
    def name(self):
        return "notification_plugin"

    @property
    def title(self):
        return _("Notification plugins")

    @property
    def do_sort(self):
        return True


# The permissions need to be loaded dynamically on each page load instead of
# only when the plugins need to be loaded because the user may have placed
# new notification plugins in the local hierarchy.
def load_plugins(force):
    for name, attrs in watolib.load_notification_scripts().items():
        if name[0] == ".":
            continue

        declare_permission("notification_plugin.%s" % name, _u(attrs["title"]), u"",
                           ["admin", "user"])


def acknowledge_failed_notifications(timestamp):
    g_acknowledgement_time[config.user.id] = timestamp
    config.user.acknowledged_notifications = int(g_acknowledgement_time[config.user.id])
    set_modified_time()


def set_modified_time():
    global g_modified_time
    g_modified_time = time.time()


def acknowledged_time():
    if g_acknowledgement_time.get(config.user.id) is None or\
            config.user.file_modified("acknowledged_notifications") > g_modified_time:
        g_acknowledgement_time[config.user.id] = config.user.acknowledged_notifications
        set_modified_time()
        if g_acknowledgement_time[config.user.id] == 0:
            # when this timestamp is first initialized, save the current timestamp as the acknowledge
            # date. This should considerably reduce the number of log files that have to be searched
            # when retrieving the list
            acknowledge_failed_notifications(time.time())

    return g_acknowledgement_time[config.user.id]


def load_failed_notifications(before=None, after=None, stat_only=False, extra_headers=None):
    may_see_notifications =\
        config.user.may("general.see_failed_notifications") or\
        config.user.may("general.see_failed_notifications_24h")

    if not may_see_notifications:
        return [0]

    query = ["GET log"]
    if stat_only:
        query.append("Stats: log_state != 0")
    else:
        query.append("Columns: %s" % " ".join(g_columns))
        query.append("Filter: log_state != 0")

    query.extend([
        "Filter: class = 3",
        "Filter: log_type = SERVICE NOTIFICATION RESULT",
        "Filter: log_type = HOST NOTIFICATION RESULT",
        "Or: 2",
    ])

    if before is not None:
        query.append("Filter: time <= %d" % before)
    if after is not None:
        query.append("Filter: time >= %d" % after)

    if may_see_notifications:
        if config.user.may("general.see_failed_notifications"):
            horizon = config.failed_notification_horizon
        else:
            horizon = 86400
        query.append("Filter: time > %d" % (int(time.time()) - horizon))

    query_txt = "\n".join(query)

    if extra_headers is not None:
        query_txt += extra_headers

    if stat_only:
        try:
            result = sites.live().query_summed_stats(query_txt)
        except MKLivestatusNotFoundError:
            result = [0]  # Normalize the result when no site answered

        if result[0] == 0 and not sites.live().dead_sites():
            # In case there are no errors and all sites are reachable:
            # advance the users acknowledgement time
            acknowledge_failed_notifications(time.time())

        return result

    else:
        return sites.live().query(query_txt)


def render_notification_table(failed_notifications):
    with table_element() as table:
        header = dict([(name, idx) for idx, name in enumerate(g_columns)])

        for row in failed_notifications:
            table.row()
            table.text_cell(_("Time"),
                            cmk.utils.render.approx_age(time.time() - row[header['time']]))
            table.text_cell(_("Contact"), row[header['contact_name']])
            table.text_cell(_("Plugin"), row[header['type']])
            table.text_cell(_("Host"), row[header['host_name']])
            table.text_cell(_("Service"), row[header['service_description']])
            table.text_cell(_("Output"), row[header['comment']])


# TODO: We should really recode this to use the view and a normal view command / action
def render_page_confirm(acktime, prev_url, failed_notifications):
    html.header(_("Confirm failed notifications"))

    if failed_notifications:
        html.open_div(class_="really")
        html.write_text(
            _("Do you really want to acknowledge all failed notifications up to %s?") %
            cmk.utils.render.date_and_time(acktime))
        html.begin_form("confirm", method="GET", action=prev_url)
        html.hidden_field('acktime', acktime)
        html.button('_confirm', _("Yes"))
        html.end_form()
        html.close_div()

    render_notification_table(failed_notifications)

    html.footer()


@cmk.gui.pages.register("clear_failed_notifications")
def page_clear():
    acktime = html.request.get_float_input_mandatory('acktime', time.time())
    prev_url = html.get_url_input('prev_url', '')
    if html.request.var('_confirm'):
        acknowledge_failed_notifications(acktime)

        if config.user.authorized_login_sites():
            # This local import is needed for the moment
            import cmk.gui.wato.user_profile  # pylint: disable=redefined-outer-name
            cmk.gui.wato.user_profile.user_profile_async_replication_page()
            return

    failed_notifications = load_failed_notifications(before=acktime, after=acknowledged_time())
    render_page_confirm(acktime, prev_url, failed_notifications)
    if html.request.var('_confirm'):
        html.reload_sidebar()
