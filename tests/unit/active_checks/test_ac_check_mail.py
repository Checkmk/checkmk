#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from argparse import Namespace as Args
from collections.abc import Sequence
from email import message_from_string
from email.message import Message as POPIMAPMessage
from pathlib import Path
from types import ModuleType
from typing import NamedTuple
from unittest import mock

import pytest
from exchangelib import Message as EWSMessage  # type: ignore[import-untyped]

from tests.unit.import_module_hack import import_module_hack

from cmk.utils.mailbox import _active_check_main_core, MailMessages


@pytest.fixture(name="check_mail", scope="module")
def fixture_check_mail() -> ModuleType:
    return import_module_hack("active_checks/check_mail")


def create_test_email(subject: str) -> POPIMAPMessage:
    email_string = (
        'Subject: %s\r\nContent-Transfer-Encoding: quoted-printable\r\nContent-Type: text/plain; charset="iso-8859-1"\r\n\r\nThe email content\r\nis very important!\r\n'
        % subject
    )
    return message_from_string(email_string)


def create_test_email_ews(subject: str) -> EWSMessage:
    return EWSMessage(subject=subject, text_body="The email content\r\nis very important!\r\n")


class FakeArgs(NamedTuple):
    forward_method: str
    forward_host: str
    connect_timeout: int


def test_forward_to_ec_creates_spool_file_in_correct_folder(
    check_mail: ModuleType, tmp_path: Path
) -> None:
    with mock.patch.dict("os.environ", {"OMD_ROOT": str(tmp_path)}, clear=True):
        result = check_mail.forward_to_ec(
            FakeArgs(
                forward_method="spool:",
                forward_host="ut_host",
                connect_timeout=1,
            ),
            ["some_ut_message"],
        )
        assert result == (0, "Forwarded 1 messages to event console", [("messages", 1)])
        import os

        found_files = []
        for root, _folders, files in os.walk(tmp_path):
            for file in files:
                found_files.append(os.path.join(root, file))
        assert len(found_files) == 1
        assert os.path.relpath(found_files[0], str(tmp_path)).startswith(
            "var/mkeventd/spool/ut_host_"
        )


def test_ac_check_mail_main_failed_connect(check_mail: ModuleType) -> None:
    state, info, perf = _active_check_main_core(
        check_mail.create_argument_parser(),
        check_mail.check_mail,
        [
            "--fetch-server",
            "foo",
            "--fetch-username",
            "bar",
            "--fetch-password",
            "baz",
            "--connect-timeout",
            "3",
        ],
    )
    assert state == 2
    assert info.startswith("Failed to connect to fetching server foo:")
    assert perf is None


@pytest.mark.parametrize(
    "mails, expected_messages, protocol",
    [
        ({}, [], "POP3"),
        (
            {
                "1": create_test_email("Foobar"),
            },
            [
                ("<21>", "None Foobar: Foobar | The email content\x00is very important!\x00"),
            ],
            "IMAP",
        ),
        (
            {
                "2": create_test_email("Bar"),
                "1": create_test_email("Foo"),
            },
            [
                ("<21>", "None Foo: Foo | The email content\x00is very important!\x00"),
                ("<21>", "None Bar: Bar | The email content\x00is very important!\x00"),
            ],
            "IMAP",
        ),
        (
            {
                "1": create_test_email_ews("Foobar"),
            },
            [
                ("<21>", "None Foobar: Foobar | The email content\x00is very important!\x00"),
            ],
            "EWS",
        ),
        (
            {
                "2": create_test_email_ews("Bar"),
                "1": create_test_email_ews("Foo"),
            },
            [
                ("<21>", "None Foo: Foo | The email content\x00is very important!\x00"),
                ("<21>", "None Bar: Bar | The email content\x00is very important!\x00"),
            ],
            "EWS",
        ),
    ],
)
def test_ac_check_mail_prepare_messages_for_ec(
    check_mail: ModuleType,
    mails: MailMessages,
    expected_messages: Sequence[tuple[str, str]],
    protocol: str,
) -> None:
    args = Args(
        body_limit=1000,
        forward_app=None,
        forward_host=None,
        fetch_server=None,
        forward_facility=2,
    )
    messages = check_mail.prepare_messages_for_ec(args, mails, protocol)
    for message, (expected_priority, expected_message) in zip(messages, expected_messages):
        assert message.startswith(expected_priority)
        assert message.endswith(expected_message)


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
