#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry
from cmk.gui.user_notify import render_user_notification_table


@dashlet_registry.register
class NotifyUsersDashlet(Dashlet):
    """Dashlet that displays GUI notifications for users"""

    @classmethod
    def type_name(cls):
        return "notify_users"

    @classmethod
    def title(cls):
        return _("User notifications")

    @classmethod
    def description(cls):
        return _("Display GUI notifications sent to users.")

    @classmethod
    def sort_index(cls):
        return 75

    @classmethod
    def styles(cls):
        return """
.notify_users {
    width: 100%;
    height: 100%;
}"""

    def show(self):
        render_user_notification_table("dashlet")
