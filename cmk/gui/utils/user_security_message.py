#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum

from cmk.utils.mail import default_from_address, MailString, send_mail_sendmail, set_mail_headers
from cmk.utils.user import UserId

from cmk.gui import config, userdb, utils
from cmk.gui.message import message_gui


class SecurityNotificationEvent(Enum):
    password_change = "Password changed"
    webauthn_added = "Security token added"
    webauthn_removed = "Security token removed"
    totp_added = "Authenticator app added"
    totp_removed = "Authenticator app removed"
    backup_used = "Login performed with backup code"
    backup_reset = "Backup codes regenerated"
    backup_revoked = "All backup codes revoked"


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
    mail = MIMEMultipart(_charset="utf-8")
    mail.attach(MIMEText("This notification is still to be styled\n", "html", _charset="utf-8"))
    mail.attach(MIMEText("\n", "html", _charset="utf-8"))
    mail.attach(
        MIMEText(
            event.value + " at " + event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "html",
            _charset="utf-8",
        )
    )
    reply_to = ""
    send_mail_sendmail(
        set_mail_headers(
            MailString(email_address),
            MailString("Checkmk: Security Event"),
            MailString(default_from_address()),
            MailString(reply_to),
            mail,
        ),
        target=MailString(email_address),
        from_address=MailString(default_from_address()),
    )


def _send_gui(user_id: UserId, event: SecurityNotificationEvent, event_time: datetime) -> None:
    timestamp = int(event_time.timestamp())
    duration = int(config.active_config.user_security_notification_duration["max_duration"])
    message_gui(
        user_id,
        {
            "text": str(event.value),
            "dest": ("list", [user_id]),
            "methods": ["gui_hint"],
            "valid_till": timestamp + duration,  # 1 week
            "id": utils.gen_id(),
            "time": timestamp,
            "security": True,
        },
    )
