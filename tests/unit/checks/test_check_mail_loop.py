#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "item": "foo",
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", ("hans", "wurst")),
                    },
                ),
                "mail_from": None,
                "mail_to": None,
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                "--fetch-password=wurst",
                "--send-server=$HOSTADDRESS$",
                "--mail-from=None",
                "--mail-to=None",
                "--status-suffix=non-existent-testhost-foo",
            ],
        ),
        (
            {
                "item": "MailLoop_imap",
                "subject": "Some subject",
                "send_server": "smtp.gmx.de",
                "send_tls": True,
                "send_port": 42,
                "send_auth": ("me@gmx.de", ("password", "p4ssw0rd")),
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "connection": {"disable_tls": False},
                        "auth": ("basic", ("me@gmx.de", ("password", "p4ssw0rd"))),
                    },
                ),
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "connect_timeout": 23,
                "duration": (93780, 183840),
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-tls",
                "--fetch-username=me@gmx.de",
                "--fetch-password=p4ssw0rd",
                "--connect-timeout=23",
                "--send-server=smtp.gmx.de",
                "--send-tls",
                "--send-port=42",
                "--send-username=me@gmx.de",
                "--send-password=p4ssw0rd",
                "--mail-from=me_from@gmx.de",
                "--mail-to=me_to@gmx.de",
                "--status-suffix=non-existent-testhost-MailLoop_imap",
                "--warning=93780",
                "--critical=183840",
                "--subject=Some subject",
            ],
        ),
    ],
)
def test_check_mail_loop_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mail_loop")
    assert active_check.run_argument_function(params) == expected_args
