#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import email
from argparse import Namespace as Args

import pytest

from tests.testlib import import_module

from cmk.utils.mailbox import _active_check_main_core


@pytest.fixture(scope="module")
def check_mail():
    return import_module("active_checks/check_mail")


def create_test_email(subject):
    email_string = (
        'Subject: %s\r\nContent-Transfer-Encoding: quoted-printable\r\nContent-Type: text/plain; charset="iso-8859-1"\r\n\r\nThe email content\r\nis very important!\r\n'
        % subject
    )
    return email.message_from_string(email_string)


def test_ac_check_mail_main_failed_connect(check_mail) -> None:
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
    assert info.startswith("Failed to connect to foo:")
    assert perf is None


@pytest.mark.parametrize(
    "mails, expected_messages, expected_forwarded",
    [
        ({}, [], []),
        (
            {
                "1": create_test_email("Foobar"),
            },
            [
                ("<21>", "None Foobar: Foobar|The email content\x00is very important!\x00"),
            ],
            [
                "1",
            ],
        ),
        (
            {
                "2": create_test_email("Bar"),
                "1": create_test_email("Foo"),
            },
            [
                ("<21>", "None Foo: Foo|The email content\x00is very important!\x00"),
                ("<21>", "None Bar: Bar|The email content\x00is very important!\x00"),
            ],
            [
                "1",
                "2",
            ],
        ),
    ],
)
def test_ac_check_mail_prepare_messages_for_ec(
    check_mail,
    mails,
    expected_messages,
    expected_forwarded,
):
    args = Args(
        body_limit=1000,
        forward_app=None,
        forward_host=None,
        fetch_server=None,
        forward_facility=2,
    )
    messages, forwarded = check_mail.prepare_messages_for_ec(args, mails)
    assert forwarded == expected_forwarded
    for message, (expected_priority, expected_message) in zip(messages, expected_messages):
        assert message.startswith(expected_priority)
        assert message.endswith(expected_message)


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
