#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.config_generation.v1 import HostConfig, IPAddressFamily, PlainTextSecret
from cmk.plugins.mail.config_generation.mail import active_check_mail

HOST_CONFIG = HostConfig(
    name="host",
    address="127.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
)


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
                        "auth": ("basic", ("foo", ("password", "bar"))),
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=127.0.0.1",
                "--fetch-tls",
                "--fetch-port=143",
                "--fetch-username=foo",
                PlainTextSecret(value="bar", format="--fetch-password=%s"),
                "--connect-timeout=15",
            ],
            id="imap",
        ),
        pytest.param(
            {
                "service_description": "Email",
                "fetch": (
                    "EWS",
                    {
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", ("foo", ("password", "bar"))),
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=127.0.0.1",
                "--fetch-port=143",
                "--fetch-username=foo",
                PlainTextSecret(value="bar", format="--fetch-password=%s"),
                "--connect-timeout=15",
            ],
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
                            ("client_id", ("password", "client_secret"), "tenant_id"),
                        ),
                        "email_address": "foo@bar.com",
                    },
                ),
                "connect_timeout": 15,
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=host",
                "--fetch-port=143",
                "--fetch-client-id=client_id",
                PlainTextSecret(value="client_secret", format="--fetch-client-secret=%s"),
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
                PlainTextSecret(value="p4ssw0rd", format="--fetch-password=%s"),
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
                PlainTextSecret(value="p4ssw0rd", format="--fetch-password=%s"),
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
    ],
)
def test_check_mail_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = active_check_mail.parameter_parser(params)
    commands = list(active_check_mail.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
    assert commands[0].service_description == "Email"
