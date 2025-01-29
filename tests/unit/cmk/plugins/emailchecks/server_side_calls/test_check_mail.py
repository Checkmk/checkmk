#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.emailchecks.server_side_calls.check_mail import active_check_mail
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(name="myhost", ipv4_config=IPv4Config(address="0.0.0.1"))


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "connection": {"disable_tls": False, "port": 143},
                        "auth": ("basic", {"username": "foo", "password": Secret(0)}),
                    },
                ),
                "connect_timeout": 15.0,
            },
            (
                "--fetch-protocol=IMAP",
                "--fetch-server=0.0.0.1",
                "--fetch-tls",
                "--fetch-port=143",
                "--fetch-username",
                "foo",
                "--fetch-password-reference",
                Secret(0),
                "--connect-timeout=15",
            ),
            id="imap",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "EWS",
                    {
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", {"username": "foo", "password": Secret(0)}),
                    },
                ),
                "connect_timeout": 15,
            },
            (
                "--fetch-protocol=EWS",
                "--fetch-server=0.0.0.1",
                "--fetch-port=143",
                "--fetch-username",
                "foo",
                "--fetch-password-reference",
                Secret(0),
                "--connect-timeout=15",
            ),
            id="ews_no_tls",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "EWS",
                    {
                        "server": "$HOSTNAME$",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": (
                            "oauth2",
                            {
                                "client_id": "client_id",
                                "client_secret": Secret(0),
                                "tenant_id": "tenant_id",
                            },
                        ),
                        "email_address": "foo@bar.com",
                    },
                ),
                "connect_timeout": 15,
            },
            (
                "--fetch-protocol=EWS",
                "--fetch-server=$HOSTNAME$",
                "--fetch-port=143",
                "--fetch-client-id=client_id",
                "--fetch-client-secret-reference",
                Secret(0),
                "--fetch-tenant-id=tenant_id",
                "--fetch-email-address=foo@bar.com",
                "--connect-timeout=15",
            ),
            id="ews_oauth",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", {"username": "me@gmx.de", "password": Secret(0)}),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "facility": ("mail", 2),
                    "application": None,
                    "host": "me.too@checkmk.com",
                    "cleanup": ("delete", "delete"),
                },
            },
            (
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username",
                "me@gmx.de",
                "--fetch-password-reference",
                Secret(0),
                "--forward-ec",
                "--forward-facility=2",
                "--forward-host=me.too@checkmk.com",
                "--cleanup=delete",
            ),
            id="imap_with_forward",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", {"username": "me@gmx.de", "password": Secret(0)}),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "facility": ("mail", 2),
                    "host": "me.too@checkmk.com",
                    "method": ("ec", ("socket", "my_method")),
                    "match_subject": "subject",
                    "application": ("spec", "application"),
                    "body_limit": 1000,
                    "cleanup": ("move", "archive"),
                },
            },
            (
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username",
                "me@gmx.de",
                "--fetch-password-reference",
                Secret(0),
                "--forward-ec",
                "--forward-method=my_method",
                "--match-subject=subject",
                "--forward-facility=2",
                "--forward-host=me.too@checkmk.com",
                "--forward-app=application",
                "--body-limit=1000",
                "--cleanup=archive",
            ),
            id="all_parameters",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "auth": ("basic", {"username": "me@gmx.de", "password": Secret(0)}),
                        "connection": {"disable_tls": True, "port": 123},
                    },
                ),
                "forward": {
                    "method": ("syslog", {"protocol": "udp", "address": "localhost", "port": 123}),
                },
            },
            (
                "--fetch-protocol=IMAP",
                "--fetch-server=imap.gmx.de",
                "--fetch-port=123",
                "--fetch-username",
                "me@gmx.de",
                "--fetch-password-reference",
                Secret(0),
                "--forward-ec",
                "--forward-method=udp,localhost,123",
            ),
            id="syslog forwarding",
        ),
    ],
)
def test_check_mail_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str | Secret]
) -> None:
    """Tests if all required arguments are present."""
    (actual,) = active_check_mail(params, HOST_CONFIG)
    assert actual == ActiveCheckCommand(
        service_description="Email",
        command_arguments=expected_args,
    )
