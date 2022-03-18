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
                "fetch": (
                    "IMAP",
                    {
                        "connection": {"disable_tls": False, "tcp_port": 143},
                        "auth": ("foo", "bar"),
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=$HOSTADDRESS$",
                "--fetch-tls",
                "--fetch-port=143",
                "--fetch-username=foo",
                "--fetch-password=bar",
                "--connect-timeout=15",
            ],
        ),
        (
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("me@gmx.de", ("password", "p4ssw0rd")),
                        "connection": {"disable_tls": True, "tcp_port": 123},
                    },
                ),
                "forward": {
                    "facility": 2,
                    "application": None,
                    "host": "me.too@tribe29.com",
                    "cleanup": True,
                },
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username=me@gmx.de",
                "--fetch-password=p4ssw0rd",
                "--forward-ec",
                "--forward-facility=2",
                "--forward-host=me.too@tribe29.com",
                "--cleanup=delete",
            ],
        ),
    ],
)
def test_check_mail_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mail")
    assert active_check.run_argument_function(params) == expected_args
