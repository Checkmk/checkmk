#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import time
from typing import Any, Dict, List, Tuple

from six import ensure_str

import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.i18n
from cmk.gui.i18n import _, _l
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.permissions import (
    Permission,
    permission_registry,
)
from cmk.gui.exceptions import MKInternalError, MKAuthException, MKUserError
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
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
)
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.utils.urls import makeuri
from cmk.utils.notify import ensure_utf8


def get_gui_messages(user_id=None):
    if user_id is None:
        user_id = config.user.id
    path = config.config_dir + "/" + ensure_str(user_id) + '/messages.mk'
    messages = store.load_object_from_file(path, default=[])

    # Delete too old messages
    updated = False
    for index, message in enumerate(messages):
        now = time.time()
        valid_till = message.get('valid_till')
        if valid_till is not None and valid_till < now:
            messages.pop(index)
            updated = True

    if updated:
        save_gui_messages(messages)

    return messages


def delete_gui_message(msg_id):
    messages = get_gui_messages()
    for index, msg in enumerate(messages):
        if msg['id'] == msg_id:
            messages.pop(index)
    save_gui_messages(messages)


def save_gui_messages(messages, user_id=None):
    if user_id is None:
        user_id = config.user.id
    path = config.config_dir + "/" + ensure_str(user_id) + '/messages.mk'
    store.mkdir(os.path.dirname(path))
    store.save_object_to_file(path, messages)


def _notify_methods() -> Dict[str, Dict[str, Any]]:
    return {
        'gui_popup': {
            'title': _('Open window in the user interface'),
            'handler': notify_gui_msg,
        },
        'gui_hint': {
            'title': _('Show hint in the \'User\' menu'),
            'handler': notify_gui_msg,
        },
        'mail': {
            'title': _('Send an E-Mail'),
            'handler': notify_mail,
        },
        'dashlet': {
            'title': _('Show notification in dashboard element \'User notifications\''),
            'handler': notify_gui_msg,
        },
    }


permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="notify",
        title=_l("Notify Users"),
        description=_l("This permissions allows users to send notifications to the users of "
                       "the monitoring system using the web interface."),
        defaults=["admin"],
    ))


@cmk.gui.pages.register("notify")
def page_notify():
    if not config.user.may("general.notify"):
        raise MKAuthException(_("You are not allowed to use the notification module."))

    title = _('Notify users')
    breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_setup(), title)
    menu = _page_menu(breadcrumb)
    html.header(title, breadcrumb, menu)

    vs_notify = _vs_notify()

    if html.check_transaction():
        try:
            msg = vs_notify.from_html_vars("_notify")
            vs_notify.validate_value(msg, "_notify")
            _process_notify_message(msg)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("notify", method="POST")
    vs_notify.render_input_as_form("_notify", {})

    html.hidden_fields()
    html.end_form()
    html.footer()


def _page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = make_simple_form_page_menu(_("Users"),
                                      breadcrumb,
                                      form_name="notify",
                                      button_name="save",
                                      save_title=_("Send notification"))

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
        ))

    return menu


def _vs_notify():
    dest_choices: List[CascadingDropdownChoice] = [
        ('broadcast', _('Everybody (Broadcast)')),
        ('list', _('A list of specific users'),
         DualListChoice(
             choices=sorted(
                 [(uid, u.get('alias', uid)) for uid, u in config.multisite_users.items()],
                 key=lambda x: x[1].lower()),
             allow_empty=False,
         )),
        #('contactgroup', _('All members of a contact group')),
        ('online', _('All online users')),
    ]

    return Dictionary(
        elements=[
            ('text',
             TextAreaUnicode(title=_('Text'),
                             help=_('Insert the text to be sent to all reciepents.'),
                             allow_empty=False,
                             empty_text=_('You need to provide a text.'),
                             cols=50,
                             rows=10)),
            ('dest',
             CascadingDropdown(
                 title=_('Send notification to'),
                 help=_('You can send the notification to a list of multiple users, which '
                        'can be choosen out of these predefined filters.'),
                 choices=dest_choices,
             )),
            ('methods',
             ListChoice(
                 title=_('How to notify'),
                 allow_empty=False,
                 choices=[(k, v['title']) for k, v in _notify_methods().items()],
                 default_value=['popup'],
             )),
            ('valid_till',
             Optional(
                 AbsoluteDate(include_time=True,),
                 title=_('Automatically invalidate notification'),
                 label=_('Enable automatic invalidation at'),
                 help=_('It is possible to automatically delete messages when the '
                        'configured time is reached. This makes it possible to inform '
                        'users about a scheduled event but suppress the notification '
                        'after the event has happened.'),
             )),
        ],
        validate=_validate_msg,
        optional_keys=[],
    )


def _validate_msg(msg, varprefix):
    if not msg.get('methods'):
        raise MKUserError('methods', _('Please select at least one notification method.'))

    valid_methods = set(_notify_methods().keys())
    for method in msg['methods']:
        if method not in valid_methods:
            raise MKUserError('methods', _('Invalid notitification method selected.'))

    # On manually entered list of users validate the names
    if isinstance(msg['dest'], tuple) and msg['dest'][0] == 'list':
        existing = set(config.multisite_users.keys())
        for user_id in msg['dest'][1]:
            if user_id not in existing:
                raise MKUserError('dest', _('A user with the id "%s" does not exist.') % user_id)


def _process_notify_message(msg):
    msg['id'] = utils.gen_id()
    msg['time'] = time.time()

    if isinstance(msg['dest'], str):
        dest_what = msg['dest']
    else:
        dest_what = msg['dest'][0]

    if dest_what == 'broadcast':
        recipients = list(config.multisite_users.keys())
    elif dest_what == 'online':
        recipients = userdb.get_online_user_ids()
    elif dest_what == 'list':
        recipients = msg['dest'][1]
    else:
        recipients = []

    num_recipients = len(recipients)

    num_success = {}
    for method in msg['methods']:
        num_success[method] = 0

    # Now loop all notitification methods to send the notifications
    errors: Dict[str, List[Tuple]] = {}
    for user_id in recipients:
        for method in msg['methods']:
            try:
                handler = _notify_methods()[method]['handler']
                handler(user_id, msg)
                num_success[method] = num_success[method] + 1
            except MKInternalError as e:
                errors.setdefault(method, []).append((user_id, e))

    message = _('The notification has been sent via<br>')
    message += "<table>"
    for method in msg['methods']:
        message += "<tr><td>%s</td><td>to %d of %d recipients</td></tr>" %\
            (_notify_methods()[method]["title"], num_success[method], num_recipients)
    message += "</table>"

    message += _('<p>Sent notification to: %s</p>') % ', '.join(recipients)
    message += '<a href="%s">%s</a>' % (makeuri(request, []), _('Back to previous page'))
    html.show_message(HTML(message))

    if errors:
        error_message = HTML()
        for method, method_errors in errors.items():
            error_message += _("Failed to send %s notifications to the following users:") % method
            table_rows = HTML()
            for user, exception in method_errors:
                table_rows += html.render_tr(
                    html.render_td(html.render_tt(user)) + html.render_td(exception))
            error_message += html.render_table(table_rows) + html.render_br()
        html.show_error(error_message)


#   .--Notify Plugins------------------------------------------------------.
#   |    _   _       _   _  __         ____  _             _               |
#   |   | \ | | ___ | |_(_)/ _|_   _  |  _ \| |_   _  __ _(_)_ __  ___     |
#   |   |  \| |/ _ \| __| | |_| | | | | |_) | | | | |/ _` | | '_ \/ __|    |
#   |   | |\  | (_) | |_| |  _| |_| | |  __/| | |_| | (_| | | | | \__ \    |
#   |   |_| \_|\___/ \__|_|_|  \__, | |_|   |_|\__,_|\__, |_|_| |_|___/    |
#   |                          |___/                 |___/                 |
#   +----------------------------------------------------------------------+


def notify_gui_msg(user_id, msg):
    messages = get_gui_messages(user_id)
    if msg not in messages:
        messages.append(msg)
        save_gui_messages(messages, user_id)
    return True


def notify_mail(user_id, msg):
    users = userdb.load_users(lock=False)
    user = users.get(user_id)

    if not user:
        raise MKInternalError(_('This user does not exist.'))

    if not user.get('email'):
        raise MKInternalError(_('This user has no mail address configured.'))

    recipient_name = user.get('alias')
    if not recipient_name:
        recipient_name = user_id

    if config.user.id is None:
        raise Exception("no user ID")
    sender_name = users[config.user.id].get('alias')
    if not sender_name:
        sender_name = user_id

    # Code mostly taken from notify_via_email() from notify.py module
    subject = _('Checkmk: Notification')
    body = _('''Greetings %s,

%s sent you a notification:

---
%s
---

''') % (recipient_name, sender_name, msg['text'])

    if msg['valid_till']:
        body += _('This notification has been created at %s and is valid till %s.') % (
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['time'])),
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['valid_till'])))

    # FIXME: Maybe use the configured mail command for Check_MK-Notify one day
    # TODO: mail does not accept umlauts: "contains invalid character '\303'" in mail
    #       addresses. handle this correctly.
    command = ["mail", "-s", ensure_str(subject), ensure_str(user['email'])]

    ensure_utf8()

    try:
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            close_fds=True,
            encoding="utf-8",
        )
    except OSError as e:
        raise MKInternalError(
            _('Mail could not be delivered. '
              'Failed to execute command "%s": %s') % (" ".join(command), e))

    stdout, _stderr = p.communicate(input=body)
    exitcode = p.returncode
    if exitcode != 0:
        raise MKInternalError(
            _('Mail could not be delivered. Exit code of command is %r. '
              'Output is: %s') % (exitcode, stdout))
    return True
