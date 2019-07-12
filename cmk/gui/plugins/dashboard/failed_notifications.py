#!/usr/bin/env python
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

import cmk.gui.notifications as notifications
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)


@dashlet_registry.register
class FailedNotificationsDashlet(Dashlet):
    """Dashlet notifying users in case of failure to send notifications"""
    @classmethod
    def type_name(cls):
        return "notify_failed_notifications"

    @classmethod
    def title(cls):
        return _("Failed Notifications")

    @classmethod
    def description(cls):
        return _("Display GUI notifications in case notification mechanism fails")

    @classmethod
    def sort_index(cls):
        return 0

    @classmethod
    def initial_refresh_interval(cls):
        return 60

    @classmethod
    def is_selectable(cls):
        return False

    @classmethod
    def styles(cls):
        return """
.has_failed_notifications {
    width: 100%;
    height: 100%;
    overflow: auto;
    font-weight: bold;
    font-size: 14pt;

    text-align: center;
    background-color: #ff5500;
}
.failed_notifications_inner {
    display:inline-block;
    margin: auto;
    position: absolute;
    top:0; bottom:0; left:0; right:0;
    height:32px;
}"""

    def show(self):
        notdata = notifications.load_failed_notifications(after=notifications.acknowledged_time(),
                                                          stat_only=True)

        if notdata is None:
            failed_notifications = 0
        else:
            failed_notifications = notdata[0]

        if not failed_notifications:
            return

        html.open_div(class_="has_failed_notifications")
        html.open_div(class_="failed_notifications_inner")

        confirm_url = html.makeuri_contextless([], filename="clear_failed_notifications.py")
        html.icon_button(confirm_url,
                         _("Clear failed notifications"),
                         "closetimewarp",
                         target="main")

        view_url = html.makeuri_contextless([("view_name", "failed_notifications")],
                                            filename="view.py")
        html.a(_("%d failed notifications") % failed_notifications, href=view_url)

        html.close_div()
        html.close_div()
