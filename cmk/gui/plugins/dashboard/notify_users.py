#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.gui.table import table_element
import cmk.gui.notify as notify
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)


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

    @classmethod
    def script(cls):
        return """
function delete_user_notification(msg_id, btn) {
    post_url("ajax_delete_user_notification.py", "id=" + msg_id);
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
}"""

    def show(self):
        html.open_div(class_="notify_users")
        with table_element("notify_users", sortable=False, searchable=False,
                           omit_if_empty=True) as table:

            for entry in sorted(notify.get_gui_messages(), key=lambda e: e["time"], reverse=True):
                if "dashlet" not in entry["methods"]:
                    continue

                table.row()

                msg_id = entry["id"]
                datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['time']))
                message = entry["text"].replace("\n", " ")

                table.cell(_("Actions"), css="buttons", sortable=False)
                html.icon_button("",
                                 _("Delete"),
                                 "delete",
                                 onclick="delete_user_notification('%s', this);" % msg_id)

                table.text_cell(_("Message"), message)
                table.text_cell(_("Date"), datetime)

        html.close_div()
