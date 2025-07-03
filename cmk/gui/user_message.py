#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator
from typing import override

from cmk.gui import forms, message
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_message", PageUserMessage))
    page_registry.register(PageEndpoint("ajax_delete_user_message", ajax_delete_user_message))
    page_registry.register(
        PageEndpoint("ajax_acknowledge_user_message", ajax_acknowledge_user_message)
    )


class PageUserMessage(Page):
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="messages",
                    title=_("Messages"),
                    topics=[
                        PageMenuTopic(
                            title=_("Received messages"),
                            entries=list(_page_menu_entries_ack_all_messages()),
                        ),
                    ],
                ),
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

    @override
    def page(self, config: Config) -> None:
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), _("Messages"))
        make_header(html, _("Your messages"), breadcrumb, self.page_menu(breadcrumb))

        for flashed_msg in get_flashed_messages():
            html.show_message(flashed_msg.msg)

        _handle_ack_all()

        html.open_div(class_="wato user_messages")
        show_user_messages()
        html.close_div()

        html.footer()


def _handle_ack_all() -> None:
    if not transactions.check_transaction():
        return

    if request.var("_ack_all"):
        num = len([msg for msg in message.get_gui_messages() if not msg.get("acknowledged")])
        message.acknowledge_all_messages()
        flash(
            _("%d %s.")
            % (
                num,
                ungettext(
                    "received message has been acknowledged",
                    "received messages have been acknowledged",
                    num,
                ),
            )
        )
        html.reload_whole_page()


def _page_menu_entries_ack_all_messages() -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Acknowledge all"),
        icon_name="werk_ack",
        is_shortcut=True,
        is_suggested=True,
        item=make_simple_link(
            make_confirm_delete_link(
                url=makeactionuri(request, transactions, [("_ack_all", "1")]),
                title=_("Acknowledge all received messages"),
                confirm_button=_("Acknowledge all"),
            )
        ),
        is_enabled=bool([msg for msg in message.get_gui_messages() if not msg.get("acknowledged")]),
    )


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

    if user.may("general.edit_notifications"):
        yield PageMenuEntry(
            title=_("Notification rules"),
            icon_name="topic_events",
            item=make_simple_link("wato.py?mode=user_notifications_p"),
        )


def show_user_messages() -> None:
    html.open_div()

    if not (messages := [m for m in message.get_gui_messages() if "gui_hint" in m["methods"]]):
        html.show_message(_("Currently you have no received messages"))
        return

    security_count = 0
    for num, entry in enumerate(
        sorted(messages, key=lambda e: (e.get("security"), e["time"]), reverse=True)
    ):
        if entry.get("security"):
            security_count = num + 1
            forms.header(_("Security message #%d") % security_count)
        else:
            forms.header(_("Message #%d") % (num + 1 - security_count))
        forms.container()
        html.open_div(class_="container")
        msg_text = entry["text"]
        match msg_text["content_type"]:
            case "text":
                html.div(msg_text["content"].replace("\n", "<br>"), class_="text")
            case "html":
                html.div(HTML(msg_text["content"], escape=False), class_="text")

        html.open_div(class_="footer")
        html.open_div(class_="actions")
        show_message_actions(
            "gui_hint",
            entry["id"],
            is_acknowledged=bool(entry.get("acknowledged")),
            must_expire=bool(entry.get("security")),
        )
        html.close_div()

        html.open_div(class_="details")
        html.write_text(
            _("Sent on: %s, Expires on: %s")
            % (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["time"])),
                (
                    "-"
                    if (valid_till := entry["valid_till"]) is None
                    else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(valid_till))
                ),
            )
        )
        html.close_div()
        html.close_div()
        forms.end()

    html.close_div()


def show_message_actions(
    what: str,
    msg_id: str,
    is_acknowledged: bool,
    must_expire: bool,
) -> None:
    if is_acknowledged:
        html.icon("checkmark", _("Acknowledged"))
    else:
        html.icon_button(
            "",
            _("Acknowledge message"),
            "werk_ack",
            onclick="cmk.utils.acknowledge_user_message('%s');cmk.utils.reload_whole_page();"
            % msg_id,
        )

    if must_expire:
        html.icon("delete", _("Cannot be deleted manually, must expire"), cssclass="colorless")
    else:
        onclick = (
            "cmk.utils.delete_user_message('%s', this);cmk.utils.reload_whole_page();" % msg_id
            if what == "gui_hint"
            else "cmk.utils.delete_user_message('%s', this);" % msg_id
        )
        html.icon_button(
            "",
            _("Delete"),
            "delete",
            onclick=onclick,
        )


def ajax_delete_user_message(config: Config) -> None:
    check_csrf_token()
    msg_id = request.get_str_input_mandatory("id")
    message.delete_gui_message(msg_id)


def ajax_acknowledge_user_message(config: Config) -> None:
    check_csrf_token()
    msg_id = request.get_str_input_mandatory("id")
    message.acknowledge_gui_message(msg_id)
