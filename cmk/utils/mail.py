#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import os
import re
import socket
import subprocess
from email.message import Message
from email.utils import formatdate, parseaddr
from typing import TypeVar

from cmk.ccc import version as cmk_version
from cmk.ccc.store import load_text_from_file

from cmk.utils import paths


class MailString(str):
    """
    user input for Checkmk invoked emails

    MailStrings should contain no client inputed CRLF characters, these are the primary point
    of injection based attacks. This applies for both IMAP and SMTP, this validation ensures
    ASVS (v4.0) ASVS V5.2.3
    """

    # Regec for CRLF
    MAIL_STRING_REGEX = re.compile(r"[\r\n]", re.UNICODE)

    @classmethod
    def validate(cls, text: str) -> None:
        """Check if it is a valid MailString

        Checkmk offers multiple points where user's can provide input data used in
        emails sent for various reasons such as:
            Report scheduler
            Event Console's  custom actions
            License Management
            Crash Reports
            CMK notification system

        Examples:

            Ensure empty strings do not raise errors

                >>> MailString.validate("")

            Validate a variety of common expected mail data is still permitted.

                >>> MailString.validate("RE: Your server is down")
                >>> MailString.validate("Zoë@checkmk.fake")
                >>> MailString.validate("xn--hxajbheg2az3al.xn--jxalpdlp")
                >>> MailString.validate("παράδειγμα.δοκιμή")
                >>> MailString.validate("ↄ𝒽ѥ𝕔𖹬-艋く")
                >>> MailString.validate("cmkadmin")
                >>> MailString.validate("$cmkadmin")

            CRLF character test
                >>> MailString.validate("\\r\\n")
                Traceback (most recent call last):
                ...
                ValueError: CRLF characters are not allowed in mail parameters: ...

        """

        if cls.MAIL_STRING_REGEX.search(text):
            raise ValueError(f"CRLF characters are not allowed in mail parameters: {text!r}")

    def __new__(cls, text: str) -> MailString:
        """Construct a new MailString object

        Raises:
            - ValueError: Whenever the given text contains CRLF characters
        """
        cls.validate(text)
        return super().__new__(cls, text)


def send_mail_sendmail(m: Message, target: MailString, from_address: MailString | None) -> None:
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

    # Skip empty target addresses, nullmailer would fail on appliances and in
    # docker container
    if cmk_version.is_cma() or _is_containerized():
        target = MailString(",".join(list(filter(None, target.split(",")))))
    cmd += ["-i", target]

    completed_process = subprocess.run(cmd, encoding="utf-8", check=False, input=m.as_string())

    if completed_process.returncode:
        raise RuntimeError("sendmail returned with exit code: %d" % completed_process.returncode)


# duplicate from omdlib
def _is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


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
    target: MailString,
    subject: MailString,
    from_address: MailString,
    reply_to: MailString,
    mail: EmailType,
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
