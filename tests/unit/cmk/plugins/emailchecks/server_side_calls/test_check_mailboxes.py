#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.emailchecks.server_side_calls.check_mailboxes import active_check_mailboxes
from cmk.server_side_calls.v1 import HostConfig, Secret

HOST_CONFIG = HostConfig(name="my_test_host")


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "service_description": "Mailboxes",
                "fetch": (
                    "IMAP",
                    {
                        "server": "foo",
                        "connection": {
                            "disable_tls": True,
                            "port": 143,
                        },
                        "auth": ("basic", {"username": "hans", "password": Secret(0)}),
                    },
                ),
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=foo",
                "--fetch-port=143",
                "--fetch-username",
                "hans",
                "--fetch-password-reference",
                Secret(0),
            ],
        ),
        (
            {
                "service_description": "Mailboxes",
                "fetch": (
                    "EWS",
                    {
                        "server": "foo",
                        "connection": {},
                        "auth": ("basic", {"username": "hans", "password": Secret(0)}),
                    },
                ),
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=foo",
                "--fetch-tls",
                "--fetch-username",
                "hans",
                "--fetch-password-reference",
                Secret(0),
            ],
        ),
        (
            {
                "service_description": "Mailboxes",
                "fetch": (
                    "EWS",
                    {
                        "server": "foo",
                        "connection": {},
                        "auth": (
                            "oauth2",
                            {
                                "client_id": "client_id",
                                "client_secret": Secret(1),
                                "tenant_id": "tenant_id",
                            },
                        ),
                    },
                ),
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=foo",
                "--fetch-tls",
                "--fetch-client-id=client_id",
                "--fetch-client-secret-reference",
                Secret(1),
                "--fetch-tenant-id=tenant_id",
            ],
        ),
        pytest.param(
            {
                "service_description": "Mailboxes",
                "fetch": (
                    "IMAP",
                    {
                        "server": "$HOSTNAME$",
                        "connection": {
                            "disable_tls": True,
                            "disable_cert_validation": True,
                            "port": 10,
                        },
                        "auth": ("basic", {"username": "user", "password": Secret(0)}),
                    },
                ),
                "connect_timeout": 10,
                "age": ("fixed", (0, 0)),
                "age_newest": ("fixed", (0, 0)),
                "count": ("fixed", (0, 0)),
                "mailboxes": ["mailbox1", "mailbox2"],
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=$HOSTNAME$",
                "--fetch-disable-cert-validation",
                "--fetch-port=10",
                "--fetch-username",
                "user",
                "--fetch-password-reference",
                Secret(0),
                "--connect-timeout=10",
                "--warn-age-oldest=0",
                "--crit-age-oldest=0",
                "--warn-age-newest=0",
                "--crit-age-newest=0",
                "--warn-count=0",
                "--crit-count=0",
                "--mailbox=mailbox1",
                "--mailbox=mailbox2",
            ],
            id="all parameters",
        ),
    ],
)
def test_check_mailboxes_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    (command,) = active_check_mailboxes(params, HOST_CONFIG)
    assert command.command_arguments == expected_args
