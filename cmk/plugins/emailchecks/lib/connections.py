#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import binascii
import email
import email.message
import email.mime.text
import email.utils
import imaplib
import logging
import poplib
import re
import smtplib
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from email.message import Message as POPIMAPMessage
from typing import assert_never, final, Literal, Self

# Isort messes with the type annotation and creates a unused-ignore for the
# OAUTH2 and OAuth2Credentials imports.
# isort: off
from exchangelib import (
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


from cmk.plugins.emailchecks.lib.ac_args import BasicAuth, MailboxAuth, OAuth2, TRXConfig

POPIMAPMailMessages = Mapping[int, POPIMAPMessage]
EWSMailMessages = Mapping[int, EWSMessage]
MailMessages = POPIMAPMailMessages | EWSMailMessages

MailID = tuple[int, int]


class ConnectError(Exception):
    pass


class SendMailError(Exception):
    pass


class CleanupMailboxError(Exception):
    pass


class _Connection(abc.ABC):
    @final
    def __enter__(self) -> Self:
        try:
            self._connect()
        except Exception as exc:
            raise ConnectError(f"Failed to connect to server: {exc!r}") from exc
        return self

    @final
    def __exit__(self, *exc_info: object) -> Literal[False]:
        """Close the data source."""
        self._disconnect()
        return False

    @abc.abstractmethod
    def _connect(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _disconnect(self) -> None:
        raise NotImplementedError()


class EWS(_Connection):
    def __init__(
        self,
        primary_smtp_address: str,
        server: str,
        auth: MailboxAuth,
        no_cert_check: bool,
        timeout: int | None,
    ) -> None:
        self._account = _make_account(primary_smtp_address, server, auth, no_cert_check, timeout)
        self._selected_folder = self._account.inbox

    def _connect(self) -> None:
        pass

    def _disconnect(self) -> None:
        self._account.protocol.close()

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

    def mails_by_date(
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
        try:
            self._account.bulk_delete(mails.values(), delete_type="SoftDelete")
        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc

    def copy(self, mails: MailMessages, folder: str) -> None:
        folder_obj = self.add_folder(folder)
        self._account.bulk_copy(mails.values(), folder_obj)


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
        case None:
            raise RuntimeError(
                "Either Username/Passwort or ClientID/ClientSecret/TenantID have to be set"
            )
        case other:
            assert_never(other)

    if no_cert_check:
        account.protocol.HTTP_ADAPTER_CLS = ews_protocol.NoVerifyHTTPAdapter
    account.protocol.TIMEOUT = timeout

    return account


@dataclass
class SMTP(_Connection):
    server: str
    port: int
    timeout: int
    tls: bool
    auth: BasicAuth | None

    def _connect(self) -> None:
        pass

    def _disconnect(self) -> None:
        pass

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


class POP3(_Connection):
    def __init__(self, server: str, port: int, timeout: int, tls: bool, auth: BasicAuth) -> None:
        self._pop3 = (
            poplib.POP3_SSL(server, port, timeout=timeout)
            if tls
            else poplib.POP3(server, port, timeout=timeout)
        )
        self._auth = auth

    def _connect(self) -> None:
        verified_result(self._pop3.user(self._auth.username))
        verified_result(self._pop3.pass_(self._auth.password))

    def _disconnect(self) -> None:
        verified_result(self._pop3.quit())

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
        try:
            for mail_index in mails:
                verified_result(self._pop3.dele(mail_index + 1))
        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc


class IMAP(_Connection):
    def __init__(
        self, server: str, port: int, timeout: int | None, tls: bool, auth: BasicAuth
    ) -> None:
        self._imap = (
            imaplib.IMAP4_SSL(server, port, timeout=timeout)
            if tls
            else imaplib.IMAP4(server, port, timeout=timeout)
        )
        self._auth = auth

    def _connect(self) -> None:
        verified_result(self._imap.login(self._auth.username, self._auth.password))
        verified_result(self._imap.select("INBOX", readonly=False))

    def _disconnect(self) -> None:
        with suppress(imaplib.IMAP4_SSL.error, imaplib.IMAP4.error):
            verified_result(self._imap.close())
        verified_result(self._imap.logout())

    def folders(self) -> Iterable[str]:
        return self.extract_folder_names(
            e for e in verified_result(self._imap.list()) if isinstance(e, bytes)
        )

    @staticmethod
    def extract_folder_names(folder_list: Iterable[bytes]) -> Iterable[str]:
        """Takes the output of imap.list() and returns an list of decoded folder names
        >>> IMAP.extract_folder_names([b'(\\\\Trash \\\\HasNoChildren) "/" Gel&APY-scht', b'(\\\\HasNoChildren) "/" INBOX', b'(\\\\NoInferiors) "/" OUTBOX'])
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
                    mails[num] = email.message_from_bytes(data[0][1])  # type: ignore[index]
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

    def mails_by_date(
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
                for mail_id in ids[0].split()  # type: ignore[union-attr]
                for date in (self._fetch_timestamp(mail_id),)  # type: ignore[arg-type]  # FIXME
                if before is None or date <= before
            ]
            if ids and ids[0]
            else []
        )  # caused by verified_result() typing horror

    def delete(self, mails: MailMessages) -> None:
        try:
            for mail_index in mails:
                verified_result(self._imap.store(mail_index, "+FLAGS", "\\Deleted"))  # type: ignore[arg-type]  # FIXME
            self._imap.expunge()
        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc

    def copy(self, mails: MailMessages, folder: str) -> None:
        target = ""
        for level in folder.split("/"):
            target += f"{level}/"
            self._imap.create(target)
        verified_result(self._imap.copy(",".join(str(index) for index in mails), folder))


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
            )
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


def verified_result(data: object) -> Sequence[bytes | tuple[bytes, bytes]] | Sequence[str]:
    """Return the payload part of the (badly typed) result of IMAP/POP functions or eventually
    raise an exception if the result is not "OK"
    """

    if isinstance(data, tuple):
        if len(data) != 2:
            raise AssertionError(f"Expected tuple with two elements, got {data!r}")
        status, result = data
        if (isinstance(status, str) and status not in {"OK", "BYE"}) or (
            isinstance(status, bytes) and not status.startswith(b"+OK")
        ):
            raise RuntimeError(f"Server responded {data!r}")
        assert isinstance(result, list)
        if not result:
            return result  # empty list
        if not isinstance(result[0], str | bytes | tuple):
            raise TypeError(f"Can not handle this datatype {result}")
        type_first_element: tuple[type, type] | type = type(result[0])
        if type_first_element in {tuple, bytes}:
            # > Each [element] is either a bytes, or a tuple. If a tuple,
            # > then the first part is the header of the response, and
            # > the second part contains the data
            # https://docs.python.org/3/library/imaplib.html#imap4-objects
            type_first_element = (tuple, bytes)
        if not all(isinstance(e, type_first_element) for e in result):
            raise TypeError(f"Detected mixed types in {result}")
        return result

    if isinstance(data, bytes):
        if not data.startswith(b"+OK"):
            raise RuntimeError("Server responded %r" % data)
        return []

    raise TypeError(f"can not handle {data}")


def make_send_connection(config: TRXConfig, timeout: int) -> SMTP | EWS:
    match _make_connection(config, timeout):
        case SMTP() | EWS() as connection:
            return connection
        case other:
            raise ConnectError(f"Can't use {other.__class__.__name__} for sending.")


def make_fetch_connection(config: TRXConfig, timeout: int) -> EWS | POP3 | IMAP:
    match _make_connection(config, timeout):
        case EWS() | POP3() | IMAP() as connection:
            return connection
        case other:
            raise ConnectError(f"Can't use {other.__class__.__name__} for sending.")


def _make_connection(config: TRXConfig, timeout: int) -> EWS | IMAP | POP3 | SMTP:
    logging.debug(
        "connecting to: %r %r %r %r",
        config.protocol,
        config.server,
        config.port,
        config.tls,
    )
    try:
        match config.protocol:
            case "POP3":
                assert isinstance(config.auth, BasicAuth)
                return POP3(
                    config.server,
                    config.port,
                    timeout=timeout,
                    tls=config.tls,
                    auth=config.auth,
                )
            case "IMAP":
                assert isinstance(config.auth, BasicAuth)
                return IMAP(
                    config.server,
                    config.port,
                    timeout=timeout,
                    tls=config.tls,
                    auth=config.auth,
                )
            case "EWS":
                assert isinstance(config.auth, BasicAuth | OAuth2)
                return EWS(
                    primary_smtp_address=config.address,
                    server=config.server,
                    auth=config.auth,
                    no_cert_check=config.disable_cert_validation,
                    timeout=timeout,
                )

            case "SMTP":
                assert isinstance(config.auth, BasicAuth) or config.auth is None
                return SMTP(
                    server=config.server,
                    port=config.port,
                    timeout=timeout,
                    tls=config.tls,
                    auth=config.auth,
                )
            case other:
                assert_never(other)

    except Exception as exc:
        raise ConnectError(f"Failed to connect to server {config.server}: {exc}")
