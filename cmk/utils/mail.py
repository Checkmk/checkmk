#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
import subprocess
from email.message import Message
from email.utils import formatdate, parseaddr
from typing import TypeVar

from cmk.utils import paths
from cmk.utils import version as cmk_version
from cmk.utils.store import load_text_from_file


def send_mail_sendmail(m: Message, target: str, from_address: str | None) -> None:
    cmd = [_sendmail_path()]
    if from_address:
        # TODO this is no longer needed since firmware 1.5.6, remove it one day.
        # sendmail of the appliance can not handle "FULLNAME <my@mail.com>" format
        # TODO Currently we only see problems on appliances, so we just change
        # that handling for now.
        # If we see problems on other nullmailer sendmail implementations, we
        # could parse the man page for sendmail and see, if it contains "nullmailer" to
        # determine if nullmailer is used
        if cmk_version.is_cma():
            sender_full_name, sender_address = parseaddr(from_address)
            if sender_full_name:
                cmd += ["-F", sender_full_name]
            cmd += ["-f", sender_address]
        else:
            cmd += ["-F", from_address, "-f", from_address]
    cmd += ["-i", target]

    completed_process = subprocess.run(cmd, encoding="utf-8", check=False, input=m.as_string())

    if completed_process.returncode:
        raise RuntimeError("sendmail returned with exit code: %d" % completed_process.returncode)


def _sendmail_path() -> str:
    # We normally don't ship the sendmail command, but our notification integration tests
    # put some fake sendmail command into the site to prevent actual sending of mails.

    site_sendmail = "%s/local/bin/sendmail" % paths.omd_root
    if os.path.exists(site_sendmail):
        return site_sendmail
    return "/usr/sbin/sendmail"


def default_from_address() -> str:
    environ_default = os.environ.get("OMD_SITE", "checkmk") + "@" + socket.getfqdn()
    if cmk_version.is_cma():
        return load_text_from_file("/etc/nullmailer/default-from", environ_default).replace(
            "\n", ""
        )

    return environ_default


EmailType = TypeVar("EmailType", bound=Message)


def set_mail_headers(
    target: str, subject: str, from_address: str, reply_to: str, mail: EmailType
) -> EmailType:
    mail["Date"] = formatdate(localtime=True)
    mail["Subject"] = subject
    mail["To"] = target

    # Set a few configurable headers
    if from_address:
        mail["From"] = from_address

    if reply_to:
        mail["Reply-To"] = reply_to
    elif len(target.split(",")) > 1:
        mail["Reply-To"] = target

    mail["Auto-Submitted"] = "auto-generated"
    mail["X-Auto-Response-Suppress"] = "DR,RN,NRN,OOF,AutoReply"

    return mail
