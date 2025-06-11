#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from functools import partial

from jinja2 import Template

from cmk.ccc.user import UserId

from cmk.utils.mail import (
    Attachment,
    default_from_address,
    get_template_html,
    MailString,
    multipart_mail,
    send_mail_sendmail,
)
from cmk.utils.paths import web_dir

from cmk.gui import config, userdb, utils
from cmk.gui.i18n import _
from cmk.gui.message import Message, message_gui, MessageText

#   .--Templates-----------------------------------------------------------.
#   |            _____                    _       _                        |
#   |           |_   _|__ _ __ ___  _ __ | | __ _| |_ ___  ___             |
#   |             | |/ _ \ '_ ` _ \| '_ \| |/ _` | __/ _ \/ __|            |
#   |             | |  __/ | | | | | |_) | | (_| | ||  __/\__ \            |
#   |             |_|\___|_| |_| |_| .__/|_|\__,_|\__\___||___/            |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _security_msg_template_html(macro_func: Callable) -> Template:
    return Template(macro_func() + get_template_html())


def _security_msg_template_txt() -> Template:
    return Template("""
You received this Email because of the following event:\n\n

{{ event }} at {{event_time}}\n\n

If you are not the initiator of this event, please contact your administrator.
""")


# .
#   .--Macros--------------------------------------------------------------.
#   |                   __  __                                             |
#   |                  |  \/  | __ _  ___ _ __ ___  ___                    |
#   |                  | |\/| |/ _` |/ __| '__/ _ \/ __|                   |
#   |                  | |  | | (_| | (__| | | (_) \__ \                   |
#   |                  |_|  |_|\__,_|\___|_|  \___/|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _password_change_macro() -> str:
    return """
{% macro msg(content) %}
    Your <b>password has been successfully changed</b> at {{event_time}}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    <br><br>
    If you did not authorize this change, please reset your password
    immediately and contact the administrator of your Checkmk instance.
{% endmacro %}
    """


def _webauthn_added_macro() -> str:
    return """
{% macro msg(content) %}
    A new <b>two-factor authentication method has been successfully added</b>
    to your account:
    <br><br>
    <b>Method</b>: webauthn security token
    <br>
    <b>Time</b>: {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    <br><br>
    If you did not authorize this change, please review your account security
    settings immediately and contact the administrator of your Checkmk
    instance.
{% endmacro %}
    """


def _webauthn_removed_macro() -> str:
    return """
{% macro msg(content) %}
    A <b>two-factor authentication method has been removed</b> from your account:
    <br><br>
    <b>Method</b>: webauthn security token
    <br>
    <b>Time</b>: {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    However, for your protection, we strongly recommend that you enable
    two-factor authentication wherever possible.
    <br><br>
    If you did not authorize this change, please secure your account
    immediately by reviewing your security settings and contacting the
    administrator of your Checkmk instance.
{% endmacro %}
    """


# TODO still waiting for CMK-22437
def _totp_added_macro() -> str:
    return """
{% macro msg(content) %}
    A new <b>two-factor authentication method has been successfully added</b>
    to your account:
    <br><br>
    <b>Method</b>: authenticator app
    <br>
    <b>Time</b>: {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    <br><br>
    If you did not authorize this change, please review your account security
    settings immediately and contact the administrator of your Checkmk
    instance.
{% endmacro %}
    """


def _totp_removed_macro() -> str:
    return """
{% macro msg(content) %}
    A <b>two-factor authentication method has been removed</b> from your account:
    <br><br>
    <b>Method</b>: authenticator app
    <br>
    <b>Time</b>: {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    However, for your protection, we strongly recommend that you enable
    two-factor authentication wherever possible.
    <br><br>
    If you did not authorize this change, please secure your account
    immediately by reviewing your security settings and contacting the
    administrator of your Checkmk instance.
{% endmacro %}
    """


def _backup_used_macro() -> str:
    return """
{% macro msg(content) %}
    A <b>backup code has been used to log in to your account</b> at {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    <br><br>
    If you did not authorize this change, please secure your account
    immediately by changing your password and reviewing your security settings.
    You can also contact the administrator of the Checkmk instance.
{% endmacro %}
    """


def _backup_reset_macro() -> str:
    return """
{% macro msg(content) %}
    Your <b>backup codes have been successfully regenerated</b> at {{ event_time }}
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, please ensure you securely store
    your new backup codes, as the previous ones are now invalid.
    <br><br>
    If you did not authorize this change, please review your account security
    immediately and contact the administrator of your Checkmk instance.
{% endmacro %}
    """


def _backup_revoked_macro() -> str:
    return """
{% macro msg(content) %}
    All <b>backup codes associated with your account have been revoked</b> at
    {{ event_time }}. These codes can no longer be used for login.
    <br><br>
    We are sending this notice to ensure the privacy and security of your
    Checkmk account. If you made this change, no further action is necessary.
    You can generate new backup codes anytime in your two-factor authentication
    settings.
    <br><br>
    If you did not authorize this change, please review your account security
    immediately and contact the administrator of your Checkmk instance.
{% endmacro %}
    """


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class SecurityNotificationEvent(Enum):
    password_change = (
        _("Your Checkmk Password has been changed"),
        partial(_password_change_macro),
    )
    webauthn_added = (
        _("Two-factor authentication has been added"),
        partial(_webauthn_added_macro),
    )
    webauthn_removed = (
        _("Two-factor authentication has been removed"),
        partial(_webauthn_removed_macro),
    )
    totp_added = (
        _("Authenticator app has been added"),
        partial(_totp_added_macro),
    )
    totp_removed = (
        _("Authenticator app removed"),
        partial(_totp_removed_macro),
    )
    backup_used = (
        _("Login performed with backup code - Checkmk Security Notice"),
        partial(_backup_used_macro),
    )
    backup_reset = (
        _("Backup codes have been regenerated"),
        partial(_backup_reset_macro),
    )
    backup_revoked = (
        _("All backup codes have been revoked"),
        partial(_backup_revoked_macro),
    )


def user_friendly_gui_message(event: SecurityNotificationEvent) -> str:
    advice_message = _(
        " If this action was not triggered by you, contact your administrator for further investigation."
    )
    match event:
        case SecurityNotificationEvent.password_change:
            message = _("Your Checkmk Password has been changed.")
        case SecurityNotificationEvent.webauthn_added:
            message = _("A Two-factor security token has been added to your Checkmk account.")
        case SecurityNotificationEvent.webauthn_removed:
            message = _("A Two-factor security token has been removed from your Checkmk account.")
        case SecurityNotificationEvent.totp_added:
            message = _("A Two-factor Authenticator app has been added to your Checkmk account.")
        case SecurityNotificationEvent.totp_removed:
            message = _(
                "A Two-factor Authenticator app has been removed from your Checkmk account."
            )
        case SecurityNotificationEvent.backup_used:
            message = _("Your account has been accessed using a backup code.")
        case SecurityNotificationEvent.backup_reset:
            message = _("The backup codes associated with your account have been reset.")
        case SecurityNotificationEvent.backup_revoked:
            message = _("All backup codes associated with this account have been revoked.")
        case _:
            raise AssertionError(_("Unknown security event"))
    return message + advice_message


def send_security_message(user_id: UserId | None, event: SecurityNotificationEvent) -> None:
    users = userdb.load_users(lock=False)
    if user_id is None:
        # log
        return
    user_spec = users.get(user_id)
    event_time = datetime.now()
    try:
        if user_spec := users.get(user_id):
            if email_address := user_spec.get("email"):
                _send_mail(email_address, event, event_time)
                return
    except (FileExistsError, FileNotFoundError, RuntimeError):
        # Todo: log?
        pass
    _send_gui(user_id, event, event_time)


def _send_mail(email_address: str, event: SecurityNotificationEvent, event_time: datetime) -> None:
    attachments = _get_attachments()

    template_html = _security_msg_template_html(event.value[1])
    template_txt = _security_msg_template_txt()

    e_time = event_time.strftime("%Y-%m-%d %H:%M:%S")
    mail = multipart_mail(
        target=email_address,
        subject=event.value[0] + _(" - Checkmk Security Notice"),
        from_address=default_from_address(),
        reply_to="",
        content_txt=template_txt.render(
            event=event.value[0],
            event_time=e_time,
        ),
        content_html=template_html.render(event_time=e_time),
        attach=attachments,
    )

    send_mail_sendmail(
        m=mail,
        target=MailString(email_address),
        from_address=MailString(default_from_address()),
    )


def _get_attachments() -> list[Attachment]:
    attachments: list[Attachment] = []
    with open(web_dir / "htdocs/images/icons/checkmk_logo.png", "rb") as file:
        attachments.append(
            Attachment(what="img", name="checkmk_logo.png", contents=file.read(), how="inline")
        )
    return attachments


def _send_gui(user_id: UserId, event: SecurityNotificationEvent, event_time: datetime) -> None:
    timestamp = int(event_time.timestamp())
    duration = int(config.active_config.user_security_notification_duration["max_duration"])
    message_gui(
        user_id,
        Message(
            text=MessageText(content_type="text", content=user_friendly_gui_message(event)),
            dest=("list", [user_id]),
            methods=["gui_hint"],
            valid_till=timestamp + duration,  # 1 week
            id=utils.gen_id(),
            time=timestamp,
            security=True,
            acknowledged=False,
        ),
    )
