#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.notifications as notifications
from cmk.gui.htmllib.context import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry
from cmk.gui.utils.urls import makeuri_contextless


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
        failed_notifications = notifications.number_of_failed_notifications(
            after=notifications.acknowledged_time()
        )
        if not failed_notifications:
            return

        html.open_div(class_="has_failed_notifications")
        html.open_div(class_="failed_notifications_inner")

        confirm_url = makeuri_contextless(request, [], filename="clear_failed_notifications.py")
        html.icon_button(
            confirm_url, _("Clear failed notifications"), "closetimewarp", target="main"
        )

        view_url = makeuri_contextless(
            request,
            [("view_name", "failed_notifications")],
            filename="view.py",
        )
        html.a(_("%d failed notifications") % failed_notifications, href=view_url)

        html.close_div()
        html.close_div()
