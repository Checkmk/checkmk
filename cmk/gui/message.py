#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableSequence
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from cmk.ccc import store

import cmk.utils.paths
from cmk.utils.mail import default_from_address, MailString, send_mail_sendmail, set_mail_headers
from cmk.utils.user import UserId

from cmk.gui import userdb, utils
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    AbsoluteDate,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DictionaryModel,
    DualListChoice,
    ListChoice,
    Optional,
    TextAreaUnicode,
)

Message = DictionaryModel


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page_handler("message", page_message)


def get_gui_messages(user_id: UserId | None = None) -> MutableSequence[Message]:
    if user_id is None:
        user_id = user.ident
    path = cmk.utils.paths.profile_dir / user_id / "messages.mk"
    messages = store.load_object_from_file(path, default=[])

    # Delete too old messages and update security message durations
    updated = False
    for index, message in enumerate(messages):
        now = time.time()
        valid_till = message.get("valid_till")
        valid_from = message.get("time")
        if valid_till is not None:
            if message.get("security") and active_config.user_security_notification_duration.get(
                "update_existing_duration"
            ):
                message["valid_till"] = (
                    valid_from
                    + active_config.user_security_notification_duration.get("max_duration")
                )
                updated = True
            if valid_till < now:
                messages.pop(index)
                updated = True

    if updated:
        save_gui_messages(messages)

    return messages


def delete_gui_message(msg_id: str) -> None:
    messages = get_gui_messages()
    for index, msg in enumerate(messages):
        if msg["id"] == msg_id and "security" not in msg:
            messages.pop(index)
    save_gui_messages(messages)


def save_gui_messages(messages: MutableSequence[Message], user_id: UserId | None = None) -> None:
    if user_id is None:
        user_id = user.ident
    path = cmk.utils.paths.profile_dir / user_id / "messages.mk"
    store.mkdir(path.parent)
    store.save_object_to_file(path, messages)


def _messaging_methods() -> dict[str, dict[str, Any]]:
    return {
        "gui_popup": {
            "title": _("Show popup message"),
            "confirmation_title": _("as a popup message"),
            "handler": message_gui,
        },
        "gui_hint": {
            "title": _("Show hint in the 'User' menu"),
            "confirmation_title": _("as a hint in the 'User' menu"),
            "handler": message_gui,
        },
        "mail": {
            "title": _("Send email"),
            "confirmation_title": _("as an email"),
            "handler": message_mail,
        },
        "dashlet": {
            "title": _("Show in the dashboard element 'User messages'"),
            "confirmation_title": _("in the dashboard element 'User messages'"),
            "handler": message_gui,
        },
    }


permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="message",
        title=_l("Send user message"),
        description=_l(
            "This permission allows users to send messages to the users of "
            "the monitoring system using the web interface."
        ),
        defaults=["admin"],
    )
)


def page_message() -> None:
    if not user.may("general.message"):
        raise MKAuthException(_("You are not allowed to use the message module."))

    title = _("Send user message")
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_setup(), title)
    menu = _page_menu(breadcrumb)
    make_header(html, title, breadcrumb, menu)

    vs_message = _vs_message()

    if transactions.check_transaction():
        try:
            msg = vs_message.from_html_vars("_message")
            vs_message.validate_value(msg, "_message")
            _process_message_message(msg)
        except MKUserError as e:
            html.user_error(e)

    with html.form_context("message", method="POST"):
        vs_message.render_input_as_form("_message", {})

        html.hidden_fields()
    html.footer()


def _page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = make_simple_form_page_menu(
        _("Users"),
        breadcrumb,
        form_name="message",
        button_name="_save",
        save_title=_("Send message"),
    )

    menu.dropdowns.insert(
        1,
        PageMenuDropdown(
            name="related",
            title=_("Related"),
            topics=[
                PageMenuTopic(
                    title=_("Setup"),
                    entries=[
                        PageMenuEntry(
                            title=_("Users"),
                            icon_name="users",
                            item=make_simple_link("wato.py?mode=users"),
                        )
                    ],
                ),
            ],
        ),
    )

    return menu


def _vs_message() -> Dictionary:
    dest_choices: list[CascadingDropdownChoice] = [
        ("all_users", _("All users")),
        (
            "list",
            _("A list of specific users"),
            DualListChoice(
                choices=sorted(
                    [
                        (uid, u.get("alias", uid))
                        for uid, u in active_config.multisite_users.items()
                    ],
                    key=lambda x: x[1].lower(),
                ),
                allow_empty=False,
            ),
        ),
        # ('contactgroup', _('All members of a contact group')),
        ("online", _("All online users")),
    ]

    return Dictionary(
        elements=[
            (
                "text",
                TextAreaUnicode(
                    title=_("Message"),
                    help=_("Insert the text to be sent to all reciepents."),
                    allow_empty=False,
                    empty_text=_("You need to provide a text."),
                    cols=50,
                    rows=10,
                ),
            ),
            (
                "dest",
                CascadingDropdown(
                    title=_("Send message to"),
                    help=_(
                        "You can send the message to a list of multiple users, which "
                        "can be chosen out of these predefined filters."
                    ),
                    choices=dest_choices,
                ),
            ),
            (
                "methods",
                ListChoice(
                    title=_("Messaging methods"),
                    allow_empty=False,
                    choices=[(k, v["title"]) for k, v in _messaging_methods().items()],
                    default_value=["popup"],
                ),
            ),
            (
                "valid_till",
                Optional(
                    valuespec=AbsoluteDate(
                        include_time=True,
                        label=_("at"),
                    ),
                    title=_("Message expiration"),
                    label=_("Expire message"),
                    help=_(
                        "It is possible to automatically delete messages when the "
                        "configured time is reached. This makes it possible to inform "
                        "users about a scheduled event but suppress the message "
                        "after the event has happened."
                    ),
                ),
            ),
        ],
        validate=_validate_msg,
        optional_keys=[],
    )


def _validate_msg(msg: Message, _varprefix: str) -> None:
    if not msg.get("methods"):
        raise MKUserError("methods", _("Please select at least one messaging method."))

    valid_methods = set(_messaging_methods().keys())
    for method in msg["methods"]:
        if method not in valid_methods:
            raise MKUserError("methods", _("Invalid messaging method selected."))

    # On manually entered list of users validate the names
    if isinstance(msg["dest"], tuple) and msg["dest"][0] == "list":
        existing = set(active_config.multisite_users.keys())
        for user_id in msg["dest"][1]:
            if user_id not in existing:
                raise MKUserError("dest", _('A user with the id "%s" does not exist.') % user_id)


def _process_message_message(msg: Message) -> None:  # pylint: disable=R0912
    msg["id"] = utils.gen_id()
    msg["time"] = time.time()

    if isinstance(msg["dest"], str):
        dest_what = msg["dest"]
    else:
        dest_what = msg["dest"][0]

    if dest_what == "all_users":
        recipients = list(map(UserId, active_config.multisite_users.keys()))
    elif dest_what == "online":
        recipients = userdb.get_online_user_ids(datetime.now())
    elif dest_what == "list":
        recipients = list(map(UserId, msg["dest"][1]))
    else:
        recipients = []

    num_recipients = len(recipients)

    num_success: dict[str, int] = {}
    for method in msg["methods"]:
        num_success[method] = 0

    # Now loop all messaging methods to send the messages
    errors: dict[str, list[tuple]] = {}
    for user_id in recipients:
        for method in msg["methods"]:
            try:
                handler = _messaging_methods()[method]["handler"]
                handler(user_id, msg)
                num_success[method] = num_success[method] + 1
            except MKInternalError as e:
                errors.setdefault(method, []).append((user_id, e))

    message = HTML.with_escaping(_("The message has successfully been sent..."))
    message += HTMLWriter.render_br()

    parts = []
    for method in msg["methods"]:
        parts.append(
            HTMLWriter.render_li(
                _messaging_methods()[method]["confirmation_title"]
                + (
                    _(" for all recipients.")
                    if num_success[method] == num_recipients
                    else _(" for %d of %d recipients.") % (num_success[method], num_recipients)
                )
            )
        )

    message += HTMLWriter.render_ul(HTML.empty().join(parts))
    message += HTMLWriter.render_p(_("Recipients: %s") % ", ".join(recipients))
    html.show_message(message)

    if errors:
        error_message = HTML.empty()
        for method, method_errors in errors.items():
            error_message += _("Failed to send %s messages to the following users:") % method
            table_rows = HTML.empty()
            for user_id, exception in method_errors:
                table_rows += HTMLWriter.render_tr(
                    HTMLWriter.render_td(HTMLWriter.render_tt(user_id))
                    + HTMLWriter.render_td(str(exception))
                )
            error_message += HTMLWriter.render_table(table_rows) + HTMLWriter.render_br()
        html.show_error(error_message)


#   ---Message Plugins-------------------------------------------------------


def message_gui(user_id: UserId, msg: Message) -> bool:
    messages = get_gui_messages(user_id)
    if msg not in messages:
        messages.append(msg)
        save_gui_messages(messages, user_id)
    return True


def message_mail(user_id: UserId, msg: Message) -> bool:
    users = userdb.load_users(lock=False)
    user_spec = users.get(user_id)

    if not user_spec:
        raise MKInternalError(_("This user does not exist."))

    if not user_spec.get("email"):
        raise MKInternalError(_("This user has no mail address configured."))

    recipient_name = user_spec.get("alias")
    if not recipient_name:
        recipient_name = user_id

    if user.id is None:
        raise Exception("no user ID")
    sender_name = users[user.id].get("alias")
    if not sender_name:
        sender_name = user_id

    body = _("""Greetings %s,\n\n%s sent you a message: \n\n---\n%s\n---""") % (
        recipient_name,
        sender_name,
        msg["text"],
    )

    if msg["valid_till"]:
        body += _("This message has been created at %s and is valid till %s.") % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg["time"])),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg["valid_till"])),
        )

    mail = MIMEMultipart(_charset="utf-8")
    mail.attach(MIMEText(body.replace("\n", "\r\n"), "plain", _charset="utf-8"))
    reply_to = ""
    try:
        send_mail_sendmail(
            set_mail_headers(
                MailString(user_spec["email"]),
                MailString("Checkmk: Message"),
                MailString(default_from_address()),
                MailString(reply_to),
                mail,
            ),
            target=MailString(user_spec["email"]),
            from_address=MailString(default_from_address()),
        )
    except Exception as exc:
        raise MKInternalError(_("Mail could not be delivered: '%s'") % exc) from exc

    return True
