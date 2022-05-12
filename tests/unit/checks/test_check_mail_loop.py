#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
                    None,
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "tcp_port": 143},
                        "auth": ("hans", "wurst"),
                    },
                ),
                "mail_from": None,
                "mail_to": None,
            },
            [
                "--fetch-protocol=None",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                "--fetch-password=wurst",
                "--smtp-server=$HOSTADDRESS$",
                "--mail-from=None",
                "--mail-to=None",
                "--status-suffix=non-existent-testhost-foo",
            ],
        ),
        (
            {
                "item": "MailLoop_imap",
                "subject": "Some subject",
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
                "imap_tls": True,
                "smtp_port": 42,
                "smtp_auth": ("me@gmx.de", ("password", "p4ssw0rd")),
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "connection": {},
                        "auth": ("me@gmx.de", ("password", "p4ssw0rd")),
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
                "--smtp-server=smtp.gmx.de",
                "--smtp-tls",
                "--smtp-port=42",
                "--smtp-username=me@gmx.de",
                "--smtp-password=p4ssw0rd",
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
