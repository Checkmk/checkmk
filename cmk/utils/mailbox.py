#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
import email.utils
import imaplib
import logging
import poplib
import re
import socket
import sys
import time
import warnings
from contextlib import suppress
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import urllib3
from exchangelib import (  # type: ignore[import]
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    EWSDateTime,
    EWSTimeZone,
    protocol,
)

import cmk.utils.password_store

Args = argparse.Namespace
Status = int
PerfData = Any
CheckResult = Tuple[Status, str, PerfData]

MailIndex = int

Message = Any

MailMessages = Dict[MailIndex, Message]


class EWS:
    def __init__(self, account: Account) -> None:
        self._account = account
        self._selected_folder = self._account.inbox

    def folders(self) -> Iterable[str]:
        return list(map(lambda x: str(x.name), self._account.msg_folder_root.children))

    def select_folder(self, folder_name: str) -> int:
        self._selected_folder = self._account.msg_folder_root / folder_name
        return int(self._selected_folder.total_count)

    def mail_ids_by_date(
        self,
        *,
        before: Optional[float] = None,
        after: Optional[float] = None,
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

    def close(self) -> None:
        self._account.protocol.close()


MailBoxType = Union[poplib.POP3_SSL, poplib.POP3, imaplib.IMAP4_SSL, imaplib.IMAP4, EWS]


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
                else (b"+" + b64_buffer[1:].replace(b",", b"/") + b"-").decode("utf-7")  #
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
    b64_buffer: List[str] = []

    def encode_b64_buffer() -> bytes:
        return (
            binascii.b2a_base64("".join(b64_buffer).encode("utf-16be"))  #
            .rstrip(b"\n=")
            .replace(b"/", b",")
        )

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


def extract_folder_names(folder_list: Iterable[bytes]) -> Iterable[str]:
    """Takes the output of imap.list() and returns an list of decoded folder names
    >>> extract_folder_names([b'(\\\\Trash \\\\HasNoChildren) "/" Gel&APY-scht', b'(\\\\HasNoChildren) "/" INBOX', b'(\\\\NoInferiors) "/" OUTBOX'])
    ['Gelöscht', 'INBOX', 'OUTBOX']
    """
    pattern = re.compile(r'\((.*?)\) "(.*)" (.*)')
    mb_list = [_mutf_7_decode(e) for e in folder_list if isinstance(e, bytes)]
    return [
        match.group(3).strip('"')  #
        for mb in mb_list  #
        for match in (pattern.search(mb),)  #
        if match is not None
    ]


def verified_result(
    data: Union[Tuple[Union[bytes, str], List[Union[bytes, str]]], bytes]
) -> List[Union[bytes, str]]:
    """Return the payload part of the (badly typed) result of IMAP/POP functions or eventlually
    raise an exception if the result is not "OK"
    """
    if isinstance(data, tuple):
        if isinstance(data[0], str):
            assert isinstance(data[1], list)
            if not data[0] in {"OK", "BYE"}:
                raise RuntimeError("Server responded %r, %r" % (data[0], data[1]))
            return data[1]
        if isinstance(data[0], bytes):
            if not data[0].startswith(b"+OK"):
                raise RuntimeError("Server responded %r, %r" % (data[0], data[1]))
            assert isinstance(data[1], list)
            return data[1]
        raise AssertionError()
    if isinstance(data, bytes):
        if not data.startswith(b"+OK"):
            raise RuntimeError("Server responded %r" % data)
        return []
    raise AssertionError()


class Mailbox:
    """Mailbox reader supporting
    * POP3 / SNMP
    * BasicAuth login
    * TLS (or not)
    * OAuth https://stackoverflow.com/questions/5193707/use-imaplib-and-oauth-for-connection-with-gmail
            https://techcommunity.microsoft.com/t5/exchange-team-blog/improving-security-together/ba-p/805892
    """

    def __init__(self, args: Args) -> None:
        self._connection: Any = None  # TODO: Typing is quite broken below...
        self._args = args

    def __enter__(self) -> "Mailbox":
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self._close_mailbox()

    def connect(self) -> None:
        def _connect_pop3() -> None:
            connection = (poplib.POP3_SSL if self._args.fetch_tls else poplib.POP3)(
                self._args.fetch_server,
                self._args.fetch_port,
            )
            verified_result(connection.user(self._args.fetch_username))
            verified_result(connection.pass_(self._args.fetch_password))
            self._connection = connection

        def _connect_imap() -> None:
            connection = (imaplib.IMAP4_SSL if self._args.fetch_tls else imaplib.IMAP4)(
                self._args.fetch_server,
                self._args.fetch_port,
            )
            verified_result(connection.login(self._args.fetch_username, self._args.fetch_password))
            verified_result(connection.select("INBOX", readonly=False))
            self._connection = connection

        def _connect_ews() -> None:
            if self._args.no_cert_check:
                protocol.BaseProtocol.HTTP_ADAPTER_CLS = protocol.NoVerifyHTTPAdapter

            connection = EWS(
                Account(
                    primary_smtp_address=self._args.fetch_email_address
                    or self._args.fetch_username,
                    autodiscover=False,
                    access_type=DELEGATE,
                    config=Configuration(
                        server=self._args.fetch_server,
                        credentials=Credentials(
                            self._args.fetch_username,
                            self._args.fetch_password,
                        ),
                    ),
                )
            )
            self._connection = connection

        assert self._connection is None
        try:
            socket.setdefaulttimeout(self._args.connect_timeout)
            {
                "POP3": _connect_pop3,
                "IMAP": _connect_imap,
                "EWS": _connect_ews,
            }[self._args.fetch_protocol]()
        except Exception as exc:
            raise ConnectError(f"Failed to connect to {self._args.fetch_server}: {exc}")

    def inbox_protocol(self) -> str:
        if isinstance(self._connection, (poplib.POP3, poplib.POP3_SSL)):
            return "POP3"
        if isinstance(self._connection, (imaplib.IMAP4, imaplib.IMAP4_SSL)):
            return "IMAP4"
        if isinstance(self._connection, EWS):
            return "EWS"
        raise AssertionError("connection must be POP3[_SSL], IMAP4[_SSL] or EWS")

    def folders(self) -> Iterable[str]:
        """Returns names of available mailbox folders"""
        assert self._connection
        if self.inbox_protocol() == "IMAP4":
            return extract_folder_names(
                e for e in verified_result(self._connection.list()) if isinstance(e, bytes)
            )
        if self.inbox_protocol() == "EWS":
            assert isinstance(self._connection, EWS)
            return self._connection.folders()
        raise AssertionError("connection must be IMAP4[_SSL] or EWS")

    def _fetch_mails(self) -> MailMessages:
        assert self._connection is not None

        def _fetch_mails_pop3() -> MailMessages:
            return {
                i: email.message_from_bytes(
                    b"\n".join(
                        e
                        for e in verified_result(self._connection.retr(i + 1))
                        if isinstance(e, bytes)
                    )
                )
                for i in range(len(verified_result(self._connection.list())))
            }

        def _fetch_mails_imap() -> MailMessages:
            raw_messages = verified_result(self._connection.search(None, "NOT", "DELETED"))[0]
            assert isinstance(raw_messages, bytes)
            messages = raw_messages.decode().strip()
            mails: MailMessages = {}
            for num in messages.split():
                try:
                    data = verified_result(self._connection.fetch(num, "(RFC822)"))
                    if isinstance(data[0], tuple):
                        mails[num] = email.message_from_bytes(data[0][1])
                # TODO: this smells - seems like we intended to just skip this mail but this way
                #       we jump out of the for loop
                except Exception as exc:
                    raise Exception(
                        "Failed to fetch mail %s (%r). Available messages: %r"
                        % (num, exc, messages)
                    ) from exc
            return mails

        try:
            inbox_protocol = self.inbox_protocol()
            if inbox_protocol == "POP3":
                return _fetch_mails_pop3()
            if inbox_protocol == "IMAP4":
                return _fetch_mails_imap()
            raise NotImplementedError(f"Fetching mails is not implemented for {inbox_protocol}")
        except Exception as exc:
            raise FetchMailsError("Failed to check for mails: %r" % exc) from exc

    def fetch_mails(self, subject_pattern: str = "") -> MailMessages:
        """Return mails contained in the currently selected folder matching @subject_pattern"""
        pattern = re.compile(subject_pattern) if subject_pattern else None
        return {
            index: msg
            for index, msg in self._fetch_mails().items()
            if pattern is None or pattern.match(msg.get("Subject", ""))
        }

    def select_folder(self, folder_name: str) -> int:
        """Select folder @folder_name and return the number of mails contained"""
        assert self._connection
        try:
            if self.inbox_protocol() == "IMAP4":
                encoded_number = verified_result(
                    self._connection.select(_mutf_7_encode(f'"{folder_name}"'))
                )[0]
                assert isinstance(encoded_number, bytes)
                return int(encoded_number.decode())
            if self.inbox_protocol() == "EWS":
                assert isinstance(self._connection, EWS)
                return self._connection.select_folder(folder_name)
            raise AssertionError("connection must be IMAP4[_SSL] or EWS")

        except Exception as exc:
            raise FetchMailsError("Could not select folder %r: %s" % (folder_name, exc))

    def mails_by_date(
        self,
        *,
        before: Optional[float] = None,
        after: Optional[float] = None,
    ) -> Iterable[float]:
        """Retrieve mail timestamps from currently selected mailbox folder
        before: if set, mails before that timestamp (rounded down to days)
                are returned
        """
        assert self._connection is not None
        assert bool(before) != bool(after)

        def format_date(timestamp: float) -> str:
            return time.strftime("%d-%b-%Y", time.gmtime(timestamp))

        def fetch_timestamp(mail_id: str) -> int:
            # Alternative, more flexible but slower implementation using <DATE> rather than
            # <INTERNALDATE> - maybe we should make this selectable
            # msg = self._mailbox.fetch(mail_id, "(RFC822)")[1]
            # mail = email.message_from_string(msg[0][1].decode())
            # parsed = email.utils.parsedate_tz(mail["DATE"])
            # return int(time.time()) if parsed is None else email.utils.mktime_tz(parsed)
            raw_number = verified_result(self._connection.fetch(mail_id, "INTERNALDATE"))[0]
            assert isinstance(raw_number, bytes)
            # typeshed bug: https://github.com/python/typeshed/issues/7781
            return int(time.mktime(imaplib.Internaldate2tuple(raw_number)))  # type: ignore[arg-type]

        if self.inbox_protocol() == "EWS":
            assert isinstance(self._connection, EWS)
            return self._connection.mail_ids_by_date(before=before, after=after)

        if before is not None:
            # we need the age in at least minute precision, but imap search doesn't allow
            # more than day-precision, so we have to retrieve all mails from the day before the
            # relevant age and filter the result
            ids = verified_result(
                self._connection.search(
                    None,
                    "SENTBEFORE",
                    email.utils.encode_rfc2231(format_date(before + 86400)),
                )
            )

        elif after is not None:
            ids = verified_result(
                self._connection.search(
                    None,
                    "SENTSINCE",
                    email.utils.encode_rfc2231(format_date(after)),
                )
            )
        else:
            ids = verified_result(self._connection.search(None, "ALL"))

        return (
            [
                date
                for mail_id in ids[0].split()
                if isinstance(mail_id, str)  # caused by verified_result() typing horror
                for date in (fetch_timestamp(mail_id),)
                if before is None or date <= before
            ]
            if ids and ids[0]
            else []
        )

    def delete_mails(self, mails: Iterable[int]) -> None:
        assert self._connection is not None
        assert isinstance(mails, (list, tuple, set))
        try:
            if self.inbox_protocol() == "POP3":
                for mail_index in mails:
                    verified_result(self._connection.dele(mail_index + 1))
            elif self.inbox_protocol() == "IMAP4":
                for mail_index in mails:
                    verified_result(self._connection.store(mail_index, "+FLAGS", "\\Deleted"))
                self._connection.expunge()

        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc

    def copy_mails(self, mails: List[int], folder: str) -> None:
        assert self._connection and self.inbox_protocol() == "IMAP4"
        try:
            for mail_index in mails:
                # The user wants the message to be moved to the folder
                # refered by the string stored in "cleanup_messages"
                folder = folder.strip("/")

                # Create maybe missing folder hierarchy
                target = ""
                for level in folder.split("/"):
                    target += "%s/" % level
                    self._connection.create(target)

                # Copy the mail
                verified_result(self._connection.copy(str(mail_index), folder))

        except Exception as exc:
            raise CleanupMailboxError("Failed to copy mail: %r" % exc) from exc

    def _close_mailbox(self) -> None:
        if not self._connection:
            return
        if self.inbox_protocol() == "POP3":
            verified_result(self._connection.quit())
        elif self.inbox_protocol() == "IMAP4":
            with suppress(imaplib.IMAP4_SSL.error, imaplib.IMAP4.error):
                verified_result(self._connection.close())
            verified_result(self._connection.logout())
        elif self.inbox_protocol() == "EWS":
            self._connection.close()


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

    parser.add_argument(
        "--fetch-server",
        type=str,
        required=True,
        metavar="ADDRESS",
        help="Host address of the IMAP/POP3/EWS server hosting your mailbox",
    )
    parser.add_argument(
        "--fetch-username",
        type=str,
        required=True,
        metavar="USER",
        help="Username to use for IMAP/POP3/EWS",
    )
    parser.add_argument(
        "--fetch-email-address",
        type=str,
        required=False,
        metavar="EMAIL-ADDRESS",
        help="Email address (default: same as username, only effects EWS protocol)",
    )
    parser.add_argument(
        "--fetch-password",
        type=str,
        required=True,
        metavar="PASSWORD",
        help="Password to use for IMAP/POP3/EWS",
    )
    parser.add_argument(
        "--fetch-protocol",
        type=str.upper,
        choices={"IMAP", "POP3", "EWS"},
        help="Set to 'IMAP', 'POP3' or 'EWS', depending on your mailserver (default=IMAP)",
    )
    parser.add_argument(
        "--fetch-port",
        type=int,
        metavar="PORT",
        help="IMAP or POP3 port (defaults to 110/995 (TLS) for POP3"
        " 143/993 (TLS) for IMAP and 80/443 (TLS) otherwise)",
    )
    parser.add_argument(
        "--fetch-tls",
        "--fetch-ssl",
        action="store_true",
        help="Use TLS/SSL for feching the mailbox (disabled by default)",
    )
    parser.add_argument(
        "--no-cert-check", action="store_true", help="Don't enforce SSL/TLS certificate validation"
    )

    parser.add_argument("--verbose", "-v", action="count", default=0)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # we have no efficient way to control the output on stderr but at least we can return
        # UNKNOWN
        raise SystemExit(3)

    args.fetch_port = args.fetch_port or (
        (995 if args.fetch_tls else 110)
        if args.fetch_protocol == "POP3"
        else (993 if args.fetch_tls else 143)
        if args.fetch_protocol == "IMAP"
        else (443 if args.fetch_tls else 80)  # HTTP / REST (e.g. EWS)
    )
    return args


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
        level=logging.CRITICAL
        if not (args.debug or args.verbose > 0)
        else {0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG)
    )

    # when we disable certificate validation intensionally we don't want to see warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # disable anything that might write to stderr by default
    if not (args.debug or args.verbose > 0):
        if not sys.warnoptions:
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
    sys.stdout.write("%s" % text)
    if perfdata:
        sys.stdout.write(" | ")
        sys.stdout.write(" ".join("%s=%s" % (p[0], ";".join(map(str, p[1:]))) for p in perfdata))
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
