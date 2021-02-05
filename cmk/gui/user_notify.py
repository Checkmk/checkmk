#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import cmk.gui.config as config
import cmk.gui.notify as notify
import cmk.gui.pages
import cmk.utils.paths
import cmk.utils.werks

from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.globals import html, request
from cmk.gui.i18n import _
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.table import table_element
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuEntry,
    PageMenuDropdown,
    PageMenuTopic,
    make_simple_link,
)
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.utils.version import __version__
from typing import Iterator


@cmk.gui.pages.page_registry.register_page("user_notify")
class ModeUserNotifyPage(cmk.gui.pages.Page):
    def title(self) -> str:
        return _("User notifications")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("User"),
                            entries=list(_page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def page(self) -> None:
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_user(), self.title())
        html.header(self.title(), breadcrumb, self.page_menu(breadcrumb))
        render_user_notification_table("gui_hint")


def _page_menu_entries_related() -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Change password"),
        icon_name="topic_change_password",
        item=make_simple_link("user_change_pw.py"),
    )

    yield PageMenuEntry(
        title=_("Edit profile"),
        icon_name="topic_profile",
        item=make_simple_link("user_profile.py"),
    )

    if rulebased_notifications_enabled() and config.user.may('general.edit_notifications'):
        yield PageMenuEntry(
            title=_("Notification rules"),
            icon_name="topic_events",
            item=make_simple_link("wato.py?mode=user_notifications_p"),
        )


def render_user_notification_table(what: str) -> None:
    html.open_div(class_="notify_users")
    with table_element("notify_users", sortable=False, searchable=False,
                       omit_if_empty=True) as table:

        for entry in sorted(notify.get_gui_messages(), key=lambda e: e["time"], reverse=True):
            if what not in entry["methods"]:
                continue

            table.row()

            msg_id = entry["id"]
            datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['time']))
            message = entry["text"].replace("\n", " ")

            table.cell(_("Actions"), css="buttons", sortable=False)
            onclick = "cmk.utils.delete_user_notification('%s', this);cmk.utils.reload_whole_page();" % msg_id \
                    if what == "gui_hint" else "cmk.utils.delete_user_notification('%s', this);" % msg_id
            html.icon_button(
                "",
                _("Delete"),
                "delete",
                onclick=onclick,
            )

            table.text_cell(_("Message"), message)
            table.text_cell(_("Date"), datetime)

    html.close_div()


@cmk.gui.pages.register("ajax_delete_user_notification")
def ajax_delete_user_notification() -> None:
    msg_id = request.get_str_input_mandatory("id")
    notify.delete_gui_message(msg_id)
