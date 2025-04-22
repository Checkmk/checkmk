#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Email server roundtrip active check"""

import argparse
import email.utils
import logging
import os
import random
import re
import time
from collections.abc import MutableMapping
from contextlib import suppress
from email.message import Message as POPIMAPMessage
from pathlib import Path
from typing import assert_never

from exchangelib import Message as EWSMessage

from cmk.plugins.emailchecks.lib.ac_args import add_trx_arguments, parse_trx_arguments, Scope
from cmk.plugins.emailchecks.lib.connections import (
    EWS,
    MailID,
    make_fetch_connection,
    make_send_connection,
    SMTP,
)
from cmk.plugins.emailchecks.lib.utils import active_check_main, Args, CheckResult, fetch_mails

# "<sent-timestamp>-<key>" -> (sent-timestamp, key)
MailDict = MutableMapping[str, MailID]

DEPRECATION_AGE = 2 * 3600


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    add_trx_arguments(parser, Scope.SEND)

    parser.add_argument(
        "--mail-from", type=str, required=True, help="Use this mail address as sender address"
    )
    parser.add_argument(
        "--mail-to", type=str, required=True, help="Use this mail address as recipient address"
    )

    parser.add_argument(
        "--warning",
        type=int,
        metavar="AGE",
        help="Loop duration of the most recent mail in seconds or the average of "
        "all received mails within a single check to raise a WARNING state",
    )
    parser.add_argument(
        "--critical",
        type=int,
        metavar="AGE",
        default=3600,
        help="Loop duration in seconds of the most recent mail in seconds or the "
        "average of all received mails within a single check to raise a "
        "CRITICAL state",
    )

    parser.add_argument(
        "--status-dir",
        type=Path,
        metavar="PATH",
        default=(
            Path(os.environ["OMD_ROOT"]) / "var/check_mk"
            if "OMD_ROOT" in os.environ
            else Path("/tmp")  # nosec B108 # BNS:13b2c8
        ),
        help="This plug-in needs a file to store information about sent, received "
        "and expected mails. Defaults to either '/tmp/' or "
        "'/omd/sites/<sitename>/var/check_mk' when executed from within an "
        "OMD site",
    )
    parser.add_argument(
        "--status-suffix",
        type=str,
        metavar="SUFFIX",
        help="Concantenated with 'check_mail_loop.SUFFIX.status' to generate "
        "the name of the status file.",
    )

    parser.add_argument(
        "--delete-messages",
        action="store_true",
        help="Delete all messages identified as being related to this check "
        "plugin. This is disabled by default, which might make your mailbox "
        "grow when you not clean it up manually.",
    )

    parser.add_argument(
        "--subject",
        type=str,
        metavar="SUBJECT",
        default="Check_MK-Mail-Loop",
        help="You can specify the subject text.",
    )

    return parser


def load_expected_mails(status_path: Path) -> MailDict:
    with suppress(IOError):
        with status_path.open() as file:
            return {
                ts + "-" + key: (int(ts), int(key))  #
                for line in file  #
                for ts, key in (line.rstrip().split(" ", 1),)
            }
    return {}


def save_expected_mails(expected_mails: MailDict, status_path: str) -> None:
    if not expected_mails:
        return
    with open(status_path, "w") as file:
        file.write("\n".join("%d %s" % (ts, key) for ts, key in expected_mails.values()))
        file.write("\n")


def subject_and_received_timestamp_from_msg(
    msg: POPIMAPMessage | EWSMessage,
) -> tuple[str, None | int]:
    # using pattern matching here results in an mypy error that I don't understand
    if isinstance(msg, POPIMAPMessage):
        if "Received" in msg:
            parsed = email.utils.parsedate_tz(msg["Received"].split(";")[-1])
            rx_ts = email.utils.mktime_tz(parsed) if parsed else None
            return msg.get("Subject", ""), rx_ts
        return msg.get("Subject", ""), None

    if isinstance(msg, EWSMessage):
        try:
            return msg.subject, int(msg.datetime_received.timestamp())  # type: ignore[attr-defined,return-value]
        except Exception:
            return msg.subject, None  # type: ignore[return-value]

    return assert_never(msg)


def check_mails(
    warning: int,
    critical: int,
    expected_mails: MailDict,
    fetched_mails: MailDict,
) -> CheckResult:
    state = 0
    perfdata = []
    output = []

    num_pending = 0
    num_lost = 0
    durations = []
    now = int(time.time())

    # Loop all expected mails and check whether or not they have been received
    for ident, (send_ts, _unused_key) in sorted(expected_mails.items()):
        if ident in fetched_mails:
            recv_ts = fetched_mails[ident][1]
            duration = recv_ts - send_ts
            durations.append(duration)

            if critical is not None and duration >= critical:
                state = 2
            elif warning is not None and duration >= warning:
                state = max(state, 1)

            if state:
                output.append(f" (warn/crit at {warning}/{critical})")

            del expected_mails[ident]  # remove message from expect list
            # FIXME: Also remove older mails which have not yet been seen?

        elif now - send_ts >= critical:
            # drop expecting messages when older than critical threshold,
            # but keep waiting for other mails which have not yet reached it
            logging.warning(
                "found mail with critical roundtrip time: %r (%dsec)",
                ident,
                now - send_ts,
            )
            del expected_mails[ident]
            num_lost += 1
            state = 2
        else:
            num_pending += 1

    if durations:
        average = sum(durations) / len(durations)
        if len(durations) == 1:
            output.insert(0, "Mail received within %d seconds" % durations[0])
        else:
            output.insert(
                0, "Received %d mails within average of %d seconds" % (len(durations), average)
            )
        # TODO: wouldn't max(durations) be useful here?
        perfdata.append(("duration", average, warning or "", critical or ""))
    else:
        output.insert(0, "Did not receive any new mail")

    if num_lost:
        output.append("Lost: %d (Did not arrive within %d seconds)" % (num_lost, critical))

    if num_pending:
        output.append("Currently waiting for %d mails" % num_pending)

    return state, ", ".join(output), perfdata


def subject_regex(subject: str) -> re.Pattern:
    """Returns regex used for subject matching - extra function for testability"""
    return re.compile(rf"(?i)(?:re: |wg: )?{subject} ([0-9]+) ([0-9]+)")


def check_mail_roundtrip(args: Args) -> CheckResult:
    fetch = parse_trx_arguments(args, Scope.FETCH)
    send = parse_trx_arguments(args, Scope.SEND)
    timeout = int(args.connect_timeout)

    # TODO: maybe we should use cmk.utils.paths.tmp_dir?
    status_file_components = ("check_mail_loop", args.status_suffix, "status")
    status_path = args.status_dir / ".".join(filter(bool, status_file_components))
    logging.debug("status_path: '%s'", status_path)

    expected_mails = load_expected_mails(status_path) or {}
    logging.debug("expected_mails: %r", expected_mails)

    # Store the unmodified list of expected mails for later deletion
    expected_mails_keys = set(expected_mails.keys())

    # Match subjects of type "[re/was:] Check_MK-Mail-Loop <timestamp> <index>"
    re_subject = subject_regex(args.subject)

    with make_fetch_connection(fetch, timeout) as connection:
        now = int(time.time())

        def filter_subject(subject: None | str, re_pattern: re.Pattern[str]) -> None | re.Match:
            if not (match := re_pattern.match(subject or "")):
                logging.debug("ignore message with subject %r", subject)
                return None
            return match

        # create a collection of all mails with their relevant details filtered
        # by subject
        # str -> (index, rx-timestamp, subject, raw_message)
        message_details = {
            f"{tx_timestamp}-{key}": (index, rx_timestamp or now, subject, raw_message)
            # we don't filter for subject here...
            for index, raw_message in fetch_mails(connection).items()
            for subject, rx_timestamp in (subject_and_received_timestamp_from_msg(raw_message),)
            # .. because we need the groups
            if (match := filter_subject(subject, re_subject))
            for tx_timestamp, key in (match.groups(),)
        }
        logging.debug("received %d check_mail_loop messages", len(message_details))

        # relevant messages are a subset of above received messages which we expected
        relevant_mail_loop_messages = {
            ts_key: (index, rx_timestamp)
            for ts_key, (index, rx_timestamp, subject, raw_message) in message_details.items()
            if ts_key in expected_mails
        }
        logging.debug("relevant messages: %r", relevant_mail_loop_messages)

        # send a 'sensor-email' with a timestamp we expect to receive next time
        if fetch == send and isinstance(connection, SMTP | EWS):
            new_mail = connection.send_mail(
                args.subject,
                mail_from=args.mail_from,
                mail_to=args.mail_to,
                now=now,
                key=random.randint(1, 1000),
            )
        else:
            with make_send_connection(send, timeout) as send_connection:
                new_mail = send_connection.send_mail(
                    args.subject,
                    mail_from=args.mail_from,
                    mail_to=args.mail_to,
                    now=now,
                    # I am not sure what this is about. I suspect we're trying to generate a unique key? Poormans UUID?
                    key=random.randint(1, 1000),
                )
        logging.debug("sent new mail: %r", new_mail)

        expected_mails.update((new_mail,))
        state, output, perfdata = check_mails(
            args.warning,
            args.critical,
            expected_mails,  # WARNING: will be modified!
            relevant_mail_loop_messages,
        )

        save_expected_mails(expected_mails, status_path)

        deletion_candidates = {
            index: raw_message
            for ts_key, (index, rx_timestamp, _subject, raw_message) in message_details.items()
            if ts_key in expected_mails_keys or now - rx_timestamp > DEPRECATION_AGE
        }
        logging.debug(
            "candidates for deletion (expected messages + those older than %ds): %s",
            DEPRECATION_AGE,
            list(deletion_candidates.keys()),
        )
        if args.delete_messages:
            # Do not delete all messages in the inbox. Only the ones which were
            # processed before! In the meantime new ones might have come in.
            logging.debug("delete messages...")
            connection.delete(deletion_candidates)  # type: ignore[arg-type]
        else:
            logging.debug("deletion not active (--delete-messages not provided)")

    return state, output, perfdata


def main() -> None:
    logging.getLogger().name = "check_mail_loop"
    active_check_main(create_argument_parser(), check_mail_roundtrip)
