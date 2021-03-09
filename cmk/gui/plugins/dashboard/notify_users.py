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
