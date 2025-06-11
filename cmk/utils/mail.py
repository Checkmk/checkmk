#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
import subprocess
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, parseaddr
from typing import Literal, NamedTuple, TypeVar

from cmk.utils import paths
from cmk.utils import version as cmk_version
from cmk.utils.store import load_text_from_file


class MailString(str):
    pass


def send_mail_sendmail(m: Message, target: str, from_address: str | None) -> None:
    cmd = [_sendmail_path()]
    if from_address:
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
        target = ",".join(list(filter(None, target.split(","))))
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


class AttachmentNamedTuple(NamedTuple):
    what: Literal["img"]
    name: str
    contents: bytes | str
    how: str


# Keeping this for compatibility reasons
AttachmentUnNamedTuple = tuple[str, str, bytes | str, str]
AttachmentTuple = AttachmentNamedTuple | AttachmentUnNamedTuple
AttachmentList = list[AttachmentTuple]


# TODO: Just use a single EmailContent parameter.
def multipart_mail(
    target: str,
    subject: str,
    from_address: str,
    reply_to: str,
    content_txt: str,
    content_html: str,
    attach: AttachmentList | None = None,
) -> MIMEMultipart:
    if attach is None:
        attach = []

    m = MIMEMultipart("related", _charset="utf-8")

    alt = MIMEMultipart("alternative")

    # The plain text part
    txt = MIMEText(content_txt, "plain", _charset="utf-8")
    alt.attach(txt)

    # The html text part
    html = MIMEText(content_html, "html", _charset="utf-8")
    alt.attach(html)

    m.attach(alt)

    # Add all attachments
    for what, name, contents, how in attach:
        part = (
            MIMEImage(contents, name=name)
            if what == "img"
            else MIMEApplication(contents, name=name)
        )
        part.add_header("Content-ID", "<%s>" % name)
        # how must be inline or attachment
        part.add_header("Content-Disposition", how, filename=name)
        m.attach(part)

    return set_mail_headers(
        MailString(target),
        MailString(subject),
        MailString(from_address),
        MailString(reply_to),
        m,
    )
