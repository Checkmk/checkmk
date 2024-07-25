#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

"""Common module for mail related active checks
Current responsibilities include:
* common active check error output
* common active check exception handling
* check output handling
* defines common mail capabilities
* common argument parsing
* manages password store
* logging
"""

import argparse
import binascii
import email
import email.message
import email.mime.text
import email.utils
import imaplib
import logging
import poplib
import random
import re
import smtplib
import sys
import time
import warnings
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from email.message import Message as POPIMAPMessage
from typing import Any, assert_never

import urllib3

# Isort messes with the type annotation and creates a unused-ignore for the
# OAUTH2 and OAuth2Credentials imports.
# isort: off
from exchangelib import (  # type: ignore[import-untyped]
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    EWSDateTime,
    EWSTimeZone,
    Folder,
    Identity,
    IMPERSONATION,
)
from exchangelib import Message as EWSMessage
from exchangelib import OAUTH2, OAuth2Credentials
from exchangelib import protocol as ews_protocol

# isort: on

import cmk.utils.password_store

from cmk.plugins.emailchecks.lib.ac_args import (
    add_trx_arguments,
    BasicAuth,
    MailboxAuth,
    OAuth2,
    Scope,
    TRXConfig,
)

Args = argparse.Namespace
Status = int
PerfData = Any
CheckResult = tuple[Status, str, PerfData]

MailIndex = int

Message = POPIMAPMessage | EWSMessage

MailMessages = Mapping[MailIndex, Message]  # type: ignore[valid-type]
POPIMAPMailMessages = Mapping[MailIndex, POPIMAPMessage]
EWSMailMessages = Mapping[MailIndex, EWSMessage]

MailID = tuple[int, int]


class EWS:

    def __init__(
        self,
        primary_smtp_address: str,
        server: str,
        auth: MailboxAuth,
        no_cert_check: bool,
        timeout: int | None,
    ) -> None:
        self._account = self._make_account(
            primary_smtp_address, server, auth, no_cert_check, timeout
        )
        self._selected_folder = self._account.inbox

    @staticmethod
    def _make_account(
        primary_smtp_address: str,
        server: str,
        auth: MailboxAuth,
        no_cert_check: bool,
        timeout: int | None,
    ) -> Account:
        # https://ecederstrand.github.io/exchangelib/#oauth-on-office-365
        match auth:
            case OAuth2(client_id, client_secret, tenant_id):
                account = Account(
                    primary_smtp_address=primary_smtp_address,
                    autodiscover=False,
                    access_type=IMPERSONATION,
                    config=Configuration(
                        server=server,
                        credentials=OAuth2Credentials(
                            client_id=client_id,
                            client_secret=client_secret,
                            tenant_id=tenant_id,
                            identity=Identity(smtp_address=primary_smtp_address),
                        ),
                        auth_type=OAUTH2,
                    ),
                    default_timezone=EWSTimeZone("Europe/Berlin"),
                )
            case BasicAuth(username, password):
                account = Account(
                    primary_smtp_address=primary_smtp_address,
                    autodiscover=False,
                    access_type=DELEGATE,
                    config=Configuration(
                        server=server,
                        credentials=Credentials(username, password),
                    ),
                    default_timezone=EWSTimeZone("Europe/Berlin"),
                )

            case other:
                assert_never(other)

        if no_cert_check:
            account.protocol.HTTP_ADAPTER_CLS = ews_protocol.NoVerifyHTTPAdapter
        account.protocol.TIMEOUT = timeout

        return account

    def folders(self) -> Iterable[str]:
        logging.debug("Account::msg_folder_root.tree():\n%s", self._account.msg_folder_root.tree())
        logging.debug(
            "folder, [folder.children]:\n%s",
            "\n".join(
                f"{folder} {list(map(lambda x: str(x.name), folder.children))}"
                for folder in self._account.msg_folder_root.children
            ),
        )

        # Return a folders 'absolute' path as it's shown in the UI.
        # Since `.absolute` returns a path with a useless and longish prefix
        # this has to be removed.
        root_folder = f"{self._account.msg_folder_root.absolute}/"
        return [f.absolute[len(root_folder) :] for f in self._account.msg_folder_root.walk()]

    def select_folder(self, folder_name: str) -> int:
        selected_folder = self._account.msg_folder_root
        for s in folder_name.split("/"):
            selected_folder /= s
        self._selected_folder = selected_folder
        return int(self._selected_folder.total_count)

    def add_folder(self, folder_path: str) -> Folder:
        subfolder_names = folder_path.split("/")

        # Determine parent folder
        parent_folder: Folder | None = None  # default
        # Match the given folder_path to both a same-level folder and a subfolder of the inbox
        for parent_folder in [self._account.inbox.parent, self._account.inbox]:
            i = 0
            for i, fname in enumerate(subfolder_names):
                if f := next(parent_folder.glob(fname).resolve(), None):
                    if i == len(subfolder_names) - 1:  # full match - folder path already exists
                        return f
                    parent_folder = f
                else:
                    break
            if i > 0:  # break loop if at least the 1st lvl subfolder is found in the root folder
                break
        subfolder_names = subfolder_names[i:]

        # Create new subfolder(s)
        for fname in subfolder_names:
            new_folder = Folder(parent=parent_folder, name=fname)
            new_folder.save()
            parent_folder = new_folder
        return new_folder

    def mail_ids_by_date(
        self,
        *,
        before: float | None = None,
        after: float | None = None,
    ) -> Iterable[float]:
        # exchangelib needs a timezone to be applied in order to select mails by
        # date. Providing none (and thus keep the default) results in errors
        # on some machines, so we hardcode one here.
        # In order to make EWS filter correctly in different timezones we need
        # a way to configure the enforced setting and keep the defaults if
        # none are given.
        tz = EWSTimeZone("Europe/Berlin")
        dt_start = EWSDateTime.from_datetime(
            datetime.fromtimestamp(after) if after else datetime(1990, 1, 1)
        ).astimezone(tz)
        dt_end = EWSDateTime.from_datetime(
            datetime.fromtimestamp(before) if before else datetime.now()
        ).astimezone(tz)

        logging.debug("fetch mails from %s (from %s)", dt_start, after)
        logging.debug("fetch mails to   %s (from %s)", dt_end, before)

        return [
            item.datetime_sent.timestamp()
            for item in self._selected_folder.filter(datetime_received__range=(dt_start, dt_end))
        ]

    def send_mail(
        self, subject: str, mail_from: str, mail_to: str, now: int, key: int
    ) -> tuple[str, MailID]:
        """Send an email with provided content using EWS and provided oauth"""
        m = EWSMessage(
            account=self._account,
            subject=f"{subject} {now} {key}",
            author=mail_from,
            to_recipients=[mail_to],
        )
        try:
            m.send()
        except Exception as exc:
            raise SendMailError(f"Could not send email ({exc!r}).") from exc
        return f"{now}-{key}", (now, key)

    def fetch_mails(self, subject_filter: Callable[[str | None], bool]) -> EWSMailMessages:
        return {
            num: msg
            for num, msg in enumerate(self._account.inbox.all())
            if subject_filter(msg.subject)
        }

    def delete(self, mails: MailMessages) -> None:
        self._account.bulk_delete(mails.values(), delete_type="SoftDelete")

    def copy(self, mails: MailMessages, folder: str) -> None:
        folder_obj = self.add_folder(folder)
        self._account.bulk_copy(mails.values(), folder_obj)

    def close(self) -> None:
        self._account.protocol.close()


@dataclass
class SMTPConnection:
    server: str
    port: int
    timeout: int
    tls: bool
    auth: BasicAuth | None

    def send_mail(
        self, subject: str, mail_from: str, mail_to: str, now: int, key: int
    ) -> tuple[str, MailID]:
        """Send an email with provided content using SMTP and provided credentials"""
        try:
            return self._send_mail(subject, mail_from, mail_to, now, key)
        except smtplib.SMTPAuthenticationError as exc:
            match exc.smtp_code:
                case 530:
                    hint = "Looks like you have to use the --send-tls flag."
                case 535:
                    hint = "Looks like you provided the wrong credentials."
                case _:
                    hint = str(exc)
            raise SendMailError(f"Could not login to SMTP server ({hint}).") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise SendMailError(
                "Could not send email. Maybe you've sent too many mails? (%r)." % exc
            ) from exc
        except smtplib.SMTPException as exc:
            raise SendMailError(f"Could not send email ({exc!r}).") from exc

    def _send_mail(
        self, subject: str, mail_from: str, mail_to: str, now: int, key: int
    ) -> tuple[str, MailID]:
        mail = email.mime.text.MIMEText("")
        mail["From"] = mail_from
        mail["To"] = mail_to
        mail["Subject"] = f"{subject} {now} {key}"
        mail["Date"] = email.utils.formatdate(localtime=True)

        logging.debug(
            "send roundtrip mail with subject %r to %r from %r using %r",
            mail["Subject"],
            mail_to,
            mail_from,
            self,
        )

        with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as connection:
            if self.tls:
                connection.starttls()
            if self.auth:
                connection.login(self.auth.username, self.auth.password)
            connection.sendmail(mail_from, mail_to, mail.as_string())
            connection.quit()
            return f"{now}-{key}", (now, key)

    def close(self) -> None:
        # see if this can be removed after refactoring
        pass


class POP3Connection:
    def __init__(self, server: str, port: int, timeout: int, tls: bool) -> None:
        self._pop3 = (
            poplib.POP3_SSL(server, port, timeout=timeout)
            if tls
            else poplib.POP3(server, port, timeout=timeout)
        )

    def connect(self, auth: BasicAuth) -> None:
        # this is should become a context manager, of course
        verified_result(self._pop3.user(auth.username))
        verified_result(self._pop3.pass_(auth.password))

    def fetch_mails(self, subject_filter: Callable[[str | None], bool]) -> POPIMAPMailMessages:
        raw = {
            i: email.message_from_bytes(
                b"\n".join(
                    e for e in verified_result(self._pop3.retr(i + 1)) if isinstance(e, bytes)
                )
            )
            for i in range(len(verified_result(self._pop3.list())))
        }
        return {num: msg for num, msg in raw.items() if subject_filter(msg.get("Subject"))}

    def delete(self, mails: MailMessages) -> None:
        for mail_index in mails:
            verified_result(self._pop3.dele(mail_index + 1))

    def close(self) -> None:
        verified_result(self._pop3.quit())


class IMAPConnection:
    def __init__(self, server: str, port: int, timeout: int | None, tls: bool) -> None:
        self._imap = (
            imaplib.IMAP4_SSL(server, port, timeout=timeout)
            if tls
            else imaplib.IMAP4(server, port, timeout=timeout)
        )

    def connect(self, auth: BasicAuth) -> None:
        verified_result(self._imap.login(auth.username, auth.password))
        verified_result(self._imap.select("INBOX", readonly=False))

    def folders(self) -> Iterable[str]:
        return self.extract_folder_names(
            e for e in verified_result(self._imap.list()) if isinstance(e, bytes)
        )

    @staticmethod
    def extract_folder_names(folder_list: Iterable[bytes]) -> Iterable[str]:
        """Takes the output of imap.list() and returns an list of decoded folder names
        >>> IMAPConnection.extract_folder_names([b'(\\\\Trash \\\\HasNoChildren) "/" Gel&APY-scht', b'(\\\\HasNoChildren) "/" INBOX', b'(\\\\NoInferiors) "/" OUTBOX'])
        ['Gelöscht', 'INBOX', 'OUTBOX']
        """
        pattern = re.compile(r'\((.*?)\) "(.*)" (.*)')
        mb_list = [_mutf_7_decode(e) for e in folder_list if isinstance(e, bytes)]
        return [
            match.group(3).strip('"')
            for mb in mb_list
            for match in (pattern.search(mb),)
            if match is not None
        ]

    def fetch_mails(self, subject_filter: Callable[[str | None], bool]) -> POPIMAPMailMessages:
        raw_messages = verified_result(self._imap.search(None, "NOT", "DELETED"))[0]
        assert isinstance(raw_messages, bytes)
        messages = raw_messages.decode().strip()
        mails: POPIMAPMailMessages = {}
        for num in messages.split():
            try:
                data = verified_result(self._imap.fetch(num, "(RFC822)"))
                if isinstance(data[0], tuple):
                    mails[num] = email.message_from_bytes(data[0][1])
            # TODO: this smells - seems like we intended to just skip this mail but this way
            #       we jump out of the for loop
            except Exception as exc:
                raise Exception(
                    f"Failed to fetch mail {num} ({exc!r}). Available messages: {messages!r}"
                ) from exc

        return {num: msg for num, msg in mails.items() if subject_filter(msg.get("Subject"))}

    def select_folder(self, folder_name: str) -> int:
        encoded_folder = _mutf_7_encode(f'"{folder_name}"')
        encoded_number = verified_result(self._imap.select(encoded_folder))[0]  # type: ignore[arg-type]  # FIXME
        assert isinstance(encoded_number, bytes)
        return int(encoded_number.decode())

    def _fetch_timestamp(self, mail_id: str) -> int:
        # Alternative, more flexible but slower implementation using <DATE> rather than
        # <INTERNALDATE> - maybe we should make this selectable
        # msg = self._mailbox.fetch(mail_id, "(RFC822)")[1]
        # mail = email.message_from_string(msg[0][1].decode())
        # parsed = email.utils.parsedate_tz(mail["DATE"])
        # return int(time.time()) if parsed is None else email.utils.mktime_tz(parsed)
        raw_number = verified_result(self._imap.fetch(mail_id, "INTERNALDATE"))[0]
        assert isinstance(raw_number, bytes)
        time_tuple = imaplib.Internaldate2tuple(raw_number)
        assert time_tuple is not None
        return int(time.mktime(time_tuple))

    def mail_ids_by_date(
        self,
        *,
        before: float | None = None,
        after: float | None = None,
    ) -> Sequence[float]:

        def format_date(timestamp: float) -> str:
            return time.strftime("%d-%b-%Y", time.gmtime(timestamp))

        if before is not None:
            # we need the age in at least minute precision, but imap search doesn't allow
            # more than day-precision, so we have to retrieve all mails from the day before the
            # relevant age and filter the result
            ids = verified_result(
                self._imap.search(
                    None,
                    "SENTBEFORE",
                    email.utils.encode_rfc2231(format_date(before + 86400)),
                )
            )

        elif after is not None:
            # yes, "elif". We ignore 'after' in case of 'before'. We validated we don't have both.
            ids = verified_result(
                self._imap.search(
                    None,
                    "SENTSINCE",
                    email.utils.encode_rfc2231(format_date(after)),
                )
            )
        else:
            ids = verified_result(self._imap.search(None, "ALL"))

        return (
            [
                date
                for mail_id in ids[0].split()
                for date in (self._fetch_timestamp(mail_id),)  # type: ignore[arg-type]  # FIXME
                if before is None or date <= before
            ]
            if ids and ids[0]
            else []
        )  # caused by verified_result() typing horror

    def delete(self, mails: MailMessages) -> None:
        for mail_index in mails:
            verified_result(self._imap.store(mail_index, "+FLAGS", "\\Deleted"))  # type: ignore[arg-type]  # FIXME
        self._imap.expunge()

    def copy(self, mails: MailMessages, folder: str) -> None:
        target = ""
        for level in folder.split("/"):
            target += f"{level}/"
            self._imap.create(target)
        verified_result(self._imap.copy(",".join(str(index) for index in mails), folder))

    def close(self) -> None:
        with suppress(imaplib.IMAP4_SSL.error, imaplib.IMAP4.error):
            verified_result(self._imap.close())
        verified_result(self._imap.logout())


MailboxConnection = POP3Connection | IMAPConnection | EWS | SMTPConnection

MailBoxType = poplib.POP3_SSL | poplib.POP3 | imaplib.IMAP4_SSL | imaplib.IMAP4 | EWS


class ConnectError(Exception):
    pass


class FetchMailsError(Exception):
    pass


class SendMailError(Exception):
    pass


class CleanupMailboxError(Exception):
    pass


class ForwardToECError(Exception):
    pass


def _mutf_7_decode(string: bytes) -> str:
    """IMAP-UTF-7 (MUTF-7) decoder based on imapclient implementation
    >>> _mutf_7_decode(b'Gr&APYA3w-e')
    'Größe'
    """
    res = []
    b64_buffer = bytearray()
    for char in string:
        if char == ord(b"&") and not b64_buffer:
            b64_buffer.append(char)
        elif char == ord(b"-") and b64_buffer:
            res.append(
                "&"
                if len(b64_buffer) == 1
                else (b"+" + b64_buffer[1:].replace(b",", b"/") + b"-").decode("utf-7")
            )  #
            b64_buffer = bytearray()
        elif b64_buffer:
            b64_buffer.append(char)
        else:
            res.append(chr(char))
    return "".join(res)


def _mutf_7_encode(string: str) -> bytes:
    """IMAP-UTF-7 (MUTF-7) encoder based on imapclient implementation
    >>> _mutf_7_encode("Größe")
    b'Gr&APYA3w-e'
    """
    res = []
    b64_buffer: list[str] = []

    def encode_b64_buffer() -> bytes:
        return (
            binascii.b2a_base64("".join(b64_buffer).encode("utf-16be"))
            .rstrip(b"\n=")
            .replace(b"/", b",")
        )  #

    def consume_b64_buffer() -> None:
        if b64_buffer:
            res.extend([b"&", encode_b64_buffer(), b"-"])
            del b64_buffer[:]

    for c in string:
        if 0x20 <= ord(c) <= 0x7E:
            consume_b64_buffer()
            res.append(b"&-" if c == "&" else c.encode("ascii"))
        else:
            b64_buffer.append(c)

    consume_b64_buffer()
    return b"".join(res)


def verified_result(data: object) -> list[bytes | str]:  # Sequence[bytes] | Sequence[str] ?
    """Return the payload part of the (badly typed) result of IMAP/POP functions or eventually
    raise an exception if the result is not "OK"
    """

    def _parse_element(raw: object) -> bytes | str:
        if isinstance(raw, (str, bytes)):
            return raw
        raise TypeError(raw)

    if isinstance(data, tuple):
        if isinstance(data[0], str):
            if data[0] not in {"OK", "BYE"}:
                raise RuntimeError(f"Server responded {data[0]!r}, {data[1]!r}")
            assert isinstance(data[1], list)
            return [_parse_element(e) for e in data[1]]
        if isinstance(data[0], bytes):
            if not data[0].startswith(b"+OK"):
                raise RuntimeError(f"Server responded {data[0]!r}, {data[1]!r}")
            assert isinstance(data[1], list)
            return [_parse_element(e) for e in data[1]]
        raise AssertionError()
    if isinstance(data, bytes):
        if not data.startswith(b"+OK"):
            raise RuntimeError("Server responded %r" % data)
        return []
    raise TypeError(data)


class Mailbox:
    """Mailbox reader and mail sender supporting
    * POP3 / SNMP / IMAP4 / EWS
    * SMTP
    * BasicAuth login
    * TLS (or not)
    * OAuth https://stackoverflow.com/questions/5193707/use-imaplib-and-oauth-for-connection-with-gmail
            https://techcommunity.microsoft.com/t5/exchange-team-blog/improving-security-together/ba-p/805892
    """

    def __init__(self, config: TRXConfig, timeout: int, ctype: Scope) -> None:
        self._connection: MailboxConnection | None = None
        self.config = config
        self.timeout = timeout
        self._ctype = str(ctype)  # this is pointless and will go.

        logging.debug(
            "connecting to: %r %r %r %r",
            config.protocol,
            config.server,
            config.port,
            config.tls,
        )

    def __enter__(self) -> "Mailbox":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._close_mailbox()

    def connect(self) -> None:
        assert self._connection is None
        self._connection = self._connect()

    def _connect(
        self,
    ) -> MailboxConnection:
        try:
            match self.config.protocol:
                case "POP3":
                    assert isinstance(self.config.auth, BasicAuth)
                    p3_conn = POP3Connection(
                        self.config.server,
                        self.config.port,
                        timeout=self.timeout,
                        tls=self.config.tls,
                    )
                    p3_conn.connect(self.config.auth)
                    return p3_conn
                case "IMAP":
                    assert isinstance(self.config.auth, BasicAuth)
                    i_conn = IMAPConnection(
                        self.config.server,
                        self.config.port,
                        timeout=self.timeout,
                        tls=self.config.tls,
                    )
                    i_conn.connect(self.config.auth)
                    return i_conn
                case "EWS":
                    return EWS(
                        primary_smtp_address=self.config.address,
                        server=self.config.server,
                        auth=self.config.auth,
                        no_cert_check=self.config.disable_cert_validation,
                        timeout=self.timeout,
                    )

                case "SMTP":
                    return SMTPConnection(
                        server=self.config.server,
                        port=self.config.port,
                        timeout=self.timeout,
                        tls=self.config.tls,
                        auth=self.config.auth if isinstance(self.config.auth, BasicAuth) else None,
                    )
                case other:
                    raise NotImplementedError(other)
        except Exception as exc:
            raise ConnectError(f"Failed to connect to server {self.config.server}: {exc}")

    def folders(self) -> Iterable[str]:
        """Returns names of available mailbox folders"""
        match self._connection:
            case IMAPConnection() | EWS() as c:
                return c.folders()
            case _:
                raise AssertionError("connection must be IMAP4[_SSL] or EWS")

    def fetch_mails(self, subject_pattern: str = "") -> MailMessages:
        """Return mails contained in the currently selected folder matching @subject_pattern"""
        pattern = re.compile(subject_pattern) if subject_pattern else None

        def matches(subject: None | str) -> bool:
            if pattern and not pattern.match(subject or ""):
                logging.debug("filter mail with non-matching subject %r", subject)
                return False
            return True

        logging.debug("pattern used to receive mails: %s", pattern)
        try:
            match self._connection:
                case POP3Connection() | IMAPConnection() | EWS() as c:
                    return c.fetch_mails(matches)
                case other:
                    raise NotImplementedError(
                        f"Fetching mails is not implemented for {type(other)}"
                    )

        except Exception as exc:
            raise FetchMailsError("Failed to check for mails: %r" % exc) from exc

    def select_folder(self, folder_name: str) -> int:
        """Select folder @folder_name and return the number of mails contained"""
        try:
            match self._connection:
                case IMAPConnection() | EWS() as c:
                    return c.select_folder(folder_name)
                case _:
                    raise AssertionError("connection must be IMAP4[_SSL] or EWS")

        except Exception as exc:
            raise FetchMailsError(f"Could not select folder {folder_name!r}: {exc}")

    def mails_by_date(
        self,
        *,
        before: float | None = None,
        after: float | None = None,
    ) -> Iterable[float]:
        """Retrieve mail timestamps from currently selected mailbox folder
        before: if set, mails before that timestamp (rounded down to days)
                are returned
        """
        assert self._connection is not None
        assert bool(before) != bool(after)

        match self._connection:
            case None:
                raise AssertionError("No connection")
            case IMAPConnection() | EWS() as c:
                return c.mail_ids_by_date(before=before, after=after)
            case POP3Connection() | SMTPConnection():
                # resulted in attribute error for poplib.POP3
                raise NotImplementedError("POP3 does not support fetching mails by date")

            case other:
                assert_never(other)

    def delete_mails(self, mails: MailMessages) -> None:
        """Delete mails specified by @mails. Please note that for POP/IMAP we delete mails by
        index (mail.keys()) while with EWS we delete sets of EWSMessage (mail.values())"""
        if not mails:
            logging.debug("delete mails: no mails given")
            return

        logging.debug("delete mails %s", mails)
        try:
            match self._connection:
                case None:
                    raise AssertionError("No connection")
                case SMTPConnection():
                    raise NotImplementedError("Deleting mails is not implemented for SMTP")
                case connection:
                    connection.delete(mails)

        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc

    def copy_mails(self, mails: MailMessages, folder: str) -> None:
        if not mails:
            logging.debug("copy mails: no mails given")
            return
        # The user wants the message to be moved to the folder
        # refered by the string stored in "cleanup_messages"
        folder = folder.strip("/")

        try:
            match self._connection:
                case IMAPConnection() | EWS() as c:
                    c.copy(mails, folder)
                case other:
                    raise NotImplementedError(f"Copying mails is not implemented for {other!r}")
        except Exception as exc:
            raise CleanupMailboxError("Failed to copy mail: %r" % exc) from exc

    def _close_mailbox(self) -> None:
        if self._connection is not None:
            self._connection.close()

    def send_mail(self, subject: str, *, mail_from: str, mail_to: str) -> tuple[str, MailID]:
        """Send an email with provided content using either SMTP or EWS and provided credentials/oauth.
        This function just manages exceptions for _send_mail_smtp() or _send_mail_ews()"""
        now = int(time.time())
        key = random.randint(1, 1000)

        match self._connection:
            case SMTPConnection() | EWS() as c:
                return c.send_mail(subject, mail_from, mail_to, now, key)

        raise SendMailError(f"Sending mails is not implemented for {self._connection!r}")


def parse_arguments(parser: argparse.ArgumentParser, argv: Sequence[str]) -> Args:
    parser.formatter_class = argparse.RawTextHelpFormatter
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=10,
        help="Timeout in seconds for network connects (default=10)",
    )
    add_trx_arguments(parser, Scope.FETCH)

    parser.add_argument("--verbose", "-v", action="count", default=0)

    try:
        return parser.parse_args(argv)
    except SystemExit as e:
        # we have no efficient way to control the output on stderr but at least we can return
        # UNKNOWN
        raise SystemExit(3) from e


#
# The following functions could be generalized in future to apply to other active checks, too.
#


def _active_check_main_core(
    argument_parser: argparse.ArgumentParser,
    check_fn: Callable[[Args], CheckResult],
    argv: Sequence[str],
) -> CheckResult:
    """Main logic for active checks"""
    # todo argparse - exceptions?
    args = parse_arguments(argument_parser, argv)
    logging.basicConfig(
        level=(
            {0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG)
            if args.debug or args.verbose > 0
            else logging.CRITICAL
        )
    )

    # when we disable certificate validation intensionally we don't want to see warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # disable anything that might write to stderr by default
    if not args.debug and args.verbose == 0 and not sys.warnoptions:
        warnings.simplefilter("ignore")

    # Enable IMAP protocol messages on stderr
    if args.fetch_protocol == "IMAP":
        # Bug in mypy's typeshed.
        imaplib.Debug = args.verbose  # type: ignore[attr-defined]

    logging.getLogger("exchangelib").setLevel(logging.WARN)

    logging.debug("use protocol for fetching: %r", args.fetch_protocol)
    try:
        return check_fn(args)
    except (ConnectError, FetchMailsError, SendMailError, ForwardToECError) as e:
        if args.debug:
            raise
        return 3, str(e), None
    except CleanupMailboxError as e:
        if args.debug:
            raise
        return 2, str(e), None
    except Exception as e:
        if args.debug:
            raise
        return 3, "Unhandled exception: %r" % e, None


def _output_check_result(text: str, perfdata: PerfData) -> None:
    """Write check result message containing the state, a message an optionally performance data
    separated by a pipe '|' symbol:
    <MESSAGE>[ | <PERF_DATA>]
    >>> _output_check_result("Successfully connected", None)
    Successfully connected
    >>> _output_check_result("Something strange", [("name", "value1", "value2")])
    Something strange | name=value1;value2
    """
    sys.stdout.write(text)
    if perfdata:
        sys.stdout.write(" | ")
        sys.stdout.write(" ".join(f'{p[0]}={";".join(map(str, p[1:]))}' for p in perfdata))
    sys.stdout.write("\n")


def active_check_main(
    argument_parser: argparse.ArgumentParser,
    check_fn: Callable[[Args], CheckResult],
) -> None:
    """Evaluate the check, write output according to Checkmk active checks and terminate the
    program in respect to the check result:
    OK: 0
    WARN: 1
    CRIT: 2
    UNKNOWN: 3

    Because it modifies sys.argv and part of the functionality is terminating the process with
    the correct return code it's hard to test in unit tests.
    Therefore _active_check_main_core and _output_check_result should be used for unit tests since
    they are not meant to modify the system environment or terminate the process."""
    cmk.utils.password_store.replace_passwords()
    exitcode, status, perfdata = _active_check_main_core(argument_parser, check_fn, sys.argv[1:])
    _output_check_result(status, perfdata)
    raise SystemExit(exitcode)
