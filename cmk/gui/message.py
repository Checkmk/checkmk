#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from six import ensure_str

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.notify import ensure_utf8

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.htmllib.context import html
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
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    AbsoluteDate,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DualListChoice,
    ListChoice,
    Optional,
    TextAreaUnicode,
)


def get_gui_messages(user_id=None):
    if user_id is None:
        user_id = user.id
    path = cmk.utils.paths.profile_dir / user_id / "messages.mk"
    messages = store.load_object_from_file(path, default=[])

    # Delete too old messages
    updated = False
    for index, message in enumerate(messages):
        now = time.time()
        valid_till = message.get("valid_till")
        if valid_till is not None and valid_till < now:
            messages.pop(index)
            updated = True

    if updated:
        save_gui_messages(messages)

    return messages


def delete_gui_message(msg_id):
    messages = get_gui_messages()
    for index, msg in enumerate(messages):
        if msg["id"] == msg_id:
            messages.pop(index)
    save_gui_messages(messages)


def save_gui_messages(messages, user_id=None):
    if user_id is None:
        user_id = user.id
    path = cmk.utils.paths.profile_dir / user_id / "messages.mk"
    store.mkdir(path.parent)
    store.save_object_to_file(path, messages)


def _messaging_methods() -> Dict[str, Dict[str, Any]]:
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


@cmk.gui.pages.register("message")
def page_message():
    if not user.may("general.message"):
        raise MKAuthException(_("You are not allowed to use the message module."))

    title = _("Send user message")
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_setup(), title)
    menu = _page_menu(breadcrumb)
    html.header(title, breadcrumb, menu)

    vs_message = _vs_message()

    if transactions.check_transaction():
        try:
            msg = vs_message.from_html_vars("_message")
            vs_message.validate_value(msg, "_message")
            _process_message_message(msg)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("message", method="POST")
    vs_message.render_input_as_form("_message", {})

    html.hidden_fields()
    html.end_form()
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


def _vs_message():
    dest_choices: List[CascadingDropdownChoice] = [
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


def _validate_msg(msg, varprefix):
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


def _process_message_message(msg):
    msg["id"] = utils.gen_id()
    msg["time"] = time.time()

    if isinstance(msg["dest"], str):
        dest_what = msg["dest"]
    else:
        dest_what = msg["dest"][0]

    if dest_what == "all_users":
        recipients = list(active_config.multisite_users.keys())
    elif dest_what == "online":
        recipients = userdb.get_online_user_ids(datetime.now())
    elif dest_what == "list":
        recipients = msg["dest"][1]
    else:
        recipients = []

    num_recipients = len(recipients)

    num_success: Dict[str, int] = {}
    for method in msg["methods"]:
        num_success[method] = 0

    # Now loop all messaging methods to send the messages
    errors: Dict[str, List[Tuple]] = {}
    for user_id in recipients:
        for method in msg["methods"]:
            try:
                handler = _messaging_methods()[method]["handler"]
                handler(user_id, msg)
                num_success[method] = num_success[method] + 1
            except MKInternalError as e:
                errors.setdefault(method, []).append((user_id, e))

    message = escape_to_html(_("The message has successfully been sent..."))
    message += html.render_br()

    parts = []
    for method in msg["methods"]:
        parts.append(
            html.render_li(
                _messaging_methods()[method]["confirmation_title"]
                + (
                    _(" for all recipients.")
                    if num_success[method] == num_recipients
                    else _(" for %d of %d recipients.") % (num_success[method], num_recipients)
                )
            )
        )

    message += html.render_ul(HTML().join(parts))
    message += html.render_p(_("Recipients: %s") % ", ".join(recipients))
    html.show_message(message)

    if errors:
        error_message = HTML()
        for method, method_errors in errors.items():
            error_message += _("Failed to send %s messages to the following users:") % method
            table_rows = HTML()
            for user_id, exception in method_errors:
                table_rows += html.render_tr(
                    html.render_td(html.render_tt(user_id)) + html.render_td(str(exception))
                )
            error_message += html.render_table(table_rows) + html.render_br()
        html.show_error(error_message)


#   ---Message Plugins-------------------------------------------------------


def message_gui(user_id, msg):
    messages = get_gui_messages(user_id)
    if msg not in messages:
        messages.append(msg)
        save_gui_messages(messages, user_id)
    return True


def message_mail(user_id, msg):
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

    # Code mostly taken from message_via_email() from message.py module
    subject = _("Checkmk: Message")
    body = (
        _(
            """Greetings %s,

%s sent you a message:

---
%s
---

"""
        )
        % (recipient_name, sender_name, msg["text"])
    )

    if msg["valid_till"]:
        body += _("This message has been created at %s and is valid till %s.") % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg["time"])),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg["valid_till"])),
        )

    # FIXME: Maybe use the configured mail command for Check_MK-Message one day
    # TODO: mail does not accept umlauts: "contains invalid character '\303'" in mail
    #       addresses. handle this correctly.
    # ? type of user_spec seems to be Dict[str,Any]
    command = [
        "mail",
        "-s",
        subject,
        ensure_str(user_spec["email"]),  # pylint: disable= six-ensure-str-bin-call
    ]

    ensure_utf8()

    try:
        completed_process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            encoding="utf-8",
            check=False,
            input=body,
        )
    except OSError as e:
        raise MKInternalError(
            _("Mail could not be delivered. " 'Failed to execute command "%s": %s')
            % (" ".join(command), e)
        )

    if completed_process.returncode:
        raise MKInternalError(
            _("Mail could not be delivered. Exit code of command is %r. " "Output is: %s")
            % (completed_process.returncode, completed_process.stdout)
        )
    return True
