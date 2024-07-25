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
import imaplib
import logging
import random
import re
import sys
import time
import warnings
from collections.abc import Callable, Iterable, Sequence
from typing import Any, assert_never

import urllib3

import cmk.utils.password_store

from cmk.plugins.emailchecks.lib import connections
from cmk.plugins.emailchecks.lib.ac_args import add_trx_arguments, Scope

Args = argparse.Namespace
Status = int
PerfData = Any
CheckResult = tuple[Status, str, PerfData]


class FetchMailsError(Exception):
    pass


class CleanupMailboxError(Exception):
    pass


class ForwardToECError(Exception):
    pass


class Mailbox:

    def __init__(
        self, connection: connections.EWS | connections.IMAP | connections.POP3 | connections.SMTP
    ) -> None:
        self._connection = connection

    def folders(self) -> Iterable[str]:
        """Returns names of available mailbox folders"""
        match self._connection:
            case connections.IMAP() | connections.EWS() as c:
                return c.folders()
            case _:
                raise AssertionError("connection must be IMAP4[_SSL] or EWS")

    def fetch_mails(self, subject_pattern: str = "") -> connections.MailMessages:
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
                case connections.POP3() | connections.IMAP() | connections.EWS() as c:
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
                case connections.IMAP() | connections.EWS() as c:
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
        assert bool(before) != bool(after)

        match self._connection:
            case connections.IMAP() | connections.EWS() as c:
                return c.mail_ids_by_date(before=before, after=after)
            case connections.POP3() | connections.SMTP():
                # resulted in attribute error for poplib.POP3
                raise NotImplementedError("POP3 does not support fetching mails by date")

            case other:
                assert_never(other)

    def delete_mails(self, mails: connections.MailMessages) -> None:
        """Delete mails specified by @mails. Please note that for POP/IMAP we delete mails by
        index (mail.keys()) while with EWS we delete sets of EWSMessage (mail.values())"""
        if not mails:
            logging.debug("delete mails: no mails given")
            return

        logging.debug("delete mails %s", mails)
        try:
            match self._connection:
                case connections.SMTP():
                    raise NotImplementedError("Deleting mails is not implemented for SMTP")
                case connection:
                    connection.delete(mails)

        except Exception as exc:
            raise CleanupMailboxError("Failed to delete mail: %r" % exc) from exc

    def copy_mails(self, mails: connections.MailMessages, folder: str) -> None:
        if not mails:
            logging.debug("copy mails: no mails given")
            return
        # The user wants the message to be moved to the folder
        # refered by the string stored in "cleanup_messages"
        folder = folder.strip("/")

        try:
            match self._connection:
                case connections.IMAP() | connections.EWS() as c:
                    c.copy(mails, folder)
                case other:
                    raise NotImplementedError(f"Copying mails is not implemented for {other!r}")
        except Exception as exc:
            raise CleanupMailboxError("Failed to copy mail: %r" % exc) from exc

    def send_mail(
        self, subject: str, *, mail_from: str, mail_to: str
    ) -> tuple[str, connections.MailID]:
        """Send an email with provided content using either SMTP or EWS and provided credentials/oauth.
        This function just manages exceptions for _send_mail_smtp() or _send_mail_ews()"""
        now = int(time.time())
        key = random.randint(1, 1000)

        match self._connection:
            case connections.SMTP() | connections.EWS() as c:
                return c.send_mail(subject, mail_from, mail_to, now, key)

        raise connections.SendMailError(
            f"Sending mails is not implemented for {self._connection!r}"
        )


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
    except (
        connections.ConnectError,
        FetchMailsError,
        connections.SendMailError,
        ForwardToECError,
    ) as e:
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
