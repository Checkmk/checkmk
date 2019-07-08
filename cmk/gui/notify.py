#!/usr/bin/python
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

import os
import time
import subprocess
from typing import Dict, Any  # pylint: disable=unused-import

import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.default_permissions import PermissionSectionGeneral
from cmk.gui.permissions import (
    Permission,
    permission_registry,
)
from cmk.gui.exceptions import MKInternalError, MKAuthException, MKUserError
from cmk.gui.valuespec import (
    Dictionary,
    TextAreaUnicode,
    CascadingDropdown,
    ListChoice,
    Optional,
    AbsoluteDate,
    DualListChoice,
)


def get_gui_messages(user_id=None):
    if user_id is None:
        user_id = config.user.id
    path = config.config_dir + "/" + user_id.encode("utf-8") + '/messages.mk'
    messages = store.load_data_from_file(path, [])

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
    path = config.config_dir + "/" + user_id.encode("utf-8") + '/messages.mk'
    store.mkdir(os.path.dirname(path))
    store.save_data_to_file(path, messages)


def _notify_methods():
    # type: () -> Dict[str, Dict[str, Any]]
    return {
        'gui_popup': {
            'title': _('Popup Message in the GUI (shows up alert window)'),
            'handler': notify_gui_msg,
        },
        'gui_hint': {
            'title': _('Send hint to message inbox (bottom of sidebar)'),
            'handler': notify_gui_msg,
        },
        'mail': {
            'title': _('Send an E-Mail'),
            'handler': notify_mail,
        },
        'dashlet': {
            'title': _('Send hint to dashlet'),
            'handler': notify_gui_msg,
        },
    }


@permission_registry.register
class NotifyUsersPermission(Permission):
    @property
    def section(self):
        return PermissionSectionGeneral

    @property
    def permission_name(self):
        return "notify"

    @property
    def title(self):
        return _("Notify Users")

    @property
    def description(self):
        return _("This permissions allows users to send notifications to the users of "
                 "the monitoring system using the web interface.")

    @property
    def defaults(self):
        return ["admin"]


@cmk.gui.pages.register("notify")
def page_notify():
    if not config.user.may("general.notify"):
        raise MKAuthException(_("You are not allowed to use the notification module."))

    html.header(_('Notify Users'))

    html.begin_context_buttons()
    html.context_button(_("Users"), "wato.py?mode=users", "back")
    html.end_context_buttons()

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

    html.button("save", _("Send notification"))

    html.hidden_fields()
    html.end_form()
    html.footer()


def _vs_notify():
    dest_choices = [
        ('broadcast', _('Everybody (Broadcast)')),
        ('list', _('A list of specific users'),
         DualListChoice(
             choices=sorted(
                 [(uid, u.get('alias', uid)) for uid, u in config.multisite_users.items()],
                 key=lambda x: x[1].lower()),
             allow_empty=False,
         )),
        #('contactgroup', _('All members of a contact group')),
    ]

    if config.save_user_access_times:
        dest_choices.append(('online', _('All online users')))

    return Dictionary(
        elements=[
            ('text',
             TextAreaUnicode(title=_('Text'),
                             help=_('Insert the text to be sent to all reciepents.'),
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
    if not msg.get('text'):
        raise MKUserError('text', _('You need to provide a text.'))

    if not msg.get('methods'):
        raise MKUserError('methods', _('Please select at least one notification method.'))

    valid_methods = _notify_methods().keys()
    for method in msg['methods']:
        if method not in valid_methods:
            raise MKUserError('methods', _('Invalid notitification method selected.'))

    # On manually entered list of users validate the names
    if isinstance(msg['dest'], tuple) and msg['dest'][0] == 'list':
        existing = config.multisite_users.keys()
        for user_id in msg['dest'][1]:
            if user_id not in existing:
                raise MKUserError('dest', _('A user with the id "%s" does not exist.') % user_id)


def _process_notify_message(msg):
    msg['id'] = utils.gen_id()
    msg['time'] = time.time()

    # construct the list of recipients
    recipients = []

    if isinstance(msg['dest'], str):
        dest_what = msg['dest']
    else:
        dest_what = msg['dest'][0]

    if dest_what == 'broadcast':
        recipients = config.multisite_users.keys()

    elif dest_what == 'online':
        recipients = userdb.get_online_user_ids()

    elif dest_what == 'list':
        recipients = msg['dest'][1]

    num_recipients = len(recipients)

    num_success = {}
    for method in msg['methods']:
        num_success[method] = 0

    # Now loop all notitification methods to send the notifications
    errors = {}
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
    message += '<a href="%s">%s</a>' % (html.makeuri([]), _('Back to previous page'))
    html.message(HTML(message))

    if errors:
        error_message = ""
        for method, method_errors in errors.items():
            error_message += _("Failed to send %s notifications to the following users:") % method
            table_rows = ''
            for user, exception in method_errors:
                table_rows += html.render_tr(html.render_td(html.render_tt(user))\
                                             + html.render_td(exception))
            error_message += html.render_table(table_rows) + html.render_br()
        html.show_error(HTML(error_message))


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

    sender_name = users[config.user.id].get('alias')
    if not sender_name:
        sender_name = user_id

    # Code mostly taken from notify_via_email() from notify.py module
    subject = _('Check_MK: Notification')
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
    command = ["mail", "-s", subject.encode("utf-8"), user['email'].encode("utf-8")]

    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. nail detects a non-Ascii character in the mail body and
    # the specified encoding is not available, it will silently not send the mail!
    # Our resultion in future: use /usr/sbin/sendmail directly.
    # Our resultion in the present: look with locale -a for an existing UTF encoding
    # and use that.
    for encoding in os.popen("locale -a 2>/dev/null"):
        l = encoding.lower()
        if "utf8" in l or "utf-8" in l or "utf.8" in l:
            encoding = encoding.strip()
            os.putenv("LANG", encoding)
            break
    else:
        raise MKInternalError(
            _('No UTF-8 encoding found in your locale -a! Please provide C.UTF-8 encoding.'))

    try:
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE,
                             close_fds=True)
    except OSError as e:
        raise MKInternalError(
            _('Mail could not be delivered. '
              'Failed to execute command "%s": %s') % (" ".join(command), e))

    output = p.communicate(body.encode("utf-8"))[0]
    exitcode = p.returncode
    if exitcode != 0:
        raise MKInternalError(
            _('Mail could not be delivered. Exit code of command is %r. '
              'Output is: %s') % (exitcode, output))
    else:
        return True
