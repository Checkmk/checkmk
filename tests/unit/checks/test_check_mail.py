#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from .checktestlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {
                "fetch": (
                    "IMAP",
                    {
                        "connection": {"disable_tls": False, "port": 143},
                        "auth": ("basic", ("foo", "bar")),
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
            id="imap",
        ),
        pytest.param(
            {
                "fetch": (
                    "EWS",
                    {
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", ("foo", "bar")),
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=$HOSTADDRESS$",
                "--fetch-port=143",
                "--fetch-username=foo",
                "--fetch-password=bar",
                "--connect-timeout=15",
            ],
            id="ews_no_tls",
        ),
        pytest.param(
            {
                "fetch": (
                    "EWS",
                    {
                        "server": "$HOSTNAME$",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": (
                            "oauth2",
                            ("client_id", ("password", "client_secret"), "tenant_id"),
                        ),
                        "email_address": "foo@bar.com",
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=$HOSTNAME$",
                "--fetch-port=143",
                "--fetch-client-id=client_id",
                "--fetch-client-secret=client_secret",
                "--fetch-tenant-id=tenant_id",
                "--fetch-email-address=foo@bar.com",
                "--connect-timeout=15",
            ],
            id="ews_oauth",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", ("me@gmx.de", ("password", "p4ssw0rd"))),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "facility": 2,
                    "application": None,
                    "host": "me.too@checkmk.com",
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
                "--forward-host=me.too@checkmk.com",
                "--cleanup=delete",
            ],
            id="imap_with_forward",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", ("me@gmx.de", ("password", "p4ssw0rd"))),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "facility": 2,
                    "host": "me.too@checkmk.com",
                    "method": "my_method",
                    "match_subject": "subject",
                    "application": "application",
                    "body_limit": 1000,
                    "cleanup": "archive",
                },
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username=me@gmx.de",
                "--fetch-password=p4ssw0rd",
                "--forward-ec",
                "--forward-method=my_method",
                "--match-subject=subject",
                "--forward-facility=2",
                "--forward-host=me.too@checkmk.com",
                "--forward-app=application",
                "--body-limit=1000",
                "--cleanup=archive",
            ],
            id="all_parameters",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", ("me@gmx.de", ("password", "p4ssw0rd"))),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "method": ("udp", "localhost", 123),
                },
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username=me@gmx.de",
                "--fetch-password=p4ssw0rd",
                "--forward-ec",
                # I don't see how this is supposed to work.
                # The active check will try to open a TCP (!) connection to "'localhost'" on port "'123)'" AFAICT.
                "--forward-method=('udp', 'localhost', 123)",
            ],
            id="syslog forwarding",
        ),
    ],
)
def test_check_mail_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mail")
    assert active_check.run_argument_function(params) == expected_args
