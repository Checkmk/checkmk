#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.gui import message
from cmk.gui.dashboard.dashlet.base import Dashlet
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.table import table_element
from cmk.gui.user_message import show_message_actions
from cmk.gui.utils.html import HTML


class MessageUsersDashletConfig(DashletConfig): ...


class MessageUsersDashlet(Dashlet[MessageUsersDashletConfig]):
    """Dashlet that displays GUI messages for users"""

    @classmethod
    def type_name(cls) -> str:
        return "user_messages"

    @classmethod
    def title(cls) -> str:
        return _("User messages")

    @classmethod
    def description(cls) -> str:
        return _("Display GUI messages sent to users.")

    @classmethod
    def sort_index(cls) -> int:
        return 75

    def show(self) -> None:
        html.open_div()
        with table_element(
            "user_messages",
            sortable=False,
            searchable=False,
            empty_text=_("Currently you have no recieved messages"),
        ) as table:
            for entry in sorted(message.get_gui_messages(), key=lambda e: e["time"], reverse=True):
                if "dashlet" not in entry["methods"]:
                    continue

                table.row()

                table.cell(_("Actions"), css=["buttons"], sortable=False)
                show_message_actions(
                    "dashlet",
                    entry["id"],
                    is_acknowledged=bool(entry.get("acknowledged")),
                    must_expire=bool(entry.get("security")),
                )

                msg_text = entry["text"]
                match msg_text["content_type"]:
                    case "text":
                        table.cell(_("Message"), msg_text["content"].replace("\n", "<br>"))
                    case "html":
                        table.cell(_("Message"), HTML(msg_text["content"], escape=False))
                table.cell(
                    _("Sent on"),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["time"])),
                )
                table.cell(
                    _("Expires on"),
                    "-"
                    if (valid_till := entry["valid_till"]) is None
                    else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(valid_till)),
                )

        html.close_div()
