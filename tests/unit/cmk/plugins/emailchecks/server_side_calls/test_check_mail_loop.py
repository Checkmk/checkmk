#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.emailchecks.server_side_calls.check_mail_loop import active_check_mail_loop
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(
    name="non-existent-testhost",
    ipv4_config=IPv4Config(address="1.2.3.4"),
    macros={
        # 1.2.3.4 in practice, but let the test show which is used.
        "$HOSTADDRESS$": "5.6.7.8"
    },
)


def test_check_mail_loop_basic() -> None:
    raw_params = {
        "item": "MailLoop_imap",
        "subject": "Some subject",
        "send": (
            "SMTP",
            {
                "server": "smtp.gmx.de",
                "auth": {"username": "me@gmx.de", "password": Secret(0)},
                "connection": {"tls": True, "port": 42},
            },
        ),
        "fetch": (
            "IMAP",
            {
                "server": "imap.gmx.de",
                "auth": ("basic", {"username": "me@gmx.de", "password": Secret(1)}),
                "connection": {"disable_tls": False, "port": 123},
            },
        ),
        "mail_from": "me_from@gmx.de",
        "mail_to": "me_to@gmx.de",
        "connect_timeout": 23,
        "duration": ("fixed", (93780, 183840)),
    }

    (actual,) = active_check_mail_loop(raw_params, HOST_CONFIG)
    assert actual == ActiveCheckCommand(
        service_description="Mail Loop MailLoop_imap",
        command_arguments=[
            "--fetch-protocol=IMAP",
            "--fetch-server=imap.gmx.de",
            "--fetch-tls",
            "--fetch-port=123",
            "--fetch-username",
            "me@gmx.de",
            "--fetch-password-reference",
            Secret(1),
            "--connect-timeout=23",
            "--send-protocol=SMTP",
            "--send-server=smtp.gmx.de",
            "--send-port=42",
            "--send-tls",
            "--send-username",
            "me@gmx.de",
            "--send-password-reference",
            Secret(0),
            "--mail-from=me_from@gmx.de",
            "--mail-to=me_to@gmx.de",
            "--status-suffix=non-existent-testhost-MailLoop_imap",
            "--warning=93780",
            "--critical=183840",
            "--subject=Some subject",
        ],
    )


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "item": "foo",
                "send": ("SMTP", {"connection": {}}),
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", {"username": "hans", "password": Secret(0)}),
                    },
                ),
            },
            ActiveCheckCommand(
                service_description="Mail Loop foo",
                command_arguments=[
                    "--fetch-protocol=IMAP",
                    "--fetch-server=bar",
                    "--fetch-port=143",
                    "--fetch-username",
                    "hans",
                    "--fetch-password-reference",
                    Secret(0),
                    "--send-protocol=SMTP",
                    "--send-server=1.2.3.4",
                    "--mail-from=",
                    "--mail-to=",
                    "--status-suffix=non-existent-testhost-foo",
                ],
            ),
        ),
        (
            {
                "item": "MailLoop_imap",
                "subject": "Some subject",
                "send": (
                    "SMTP",
                    {
                        "server": "smtp.gmx.de",
                        "connection": {"tls": True, "port": 42},
                        "auth": {"username": "me@gmx.de", "password": Secret(1)},
                    },
                ),
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.de",
                        "connection": {"disable_tls": False},
                        "auth": ("basic", {"username": "me@gmx.de", "password": Secret(2)}),
                    },
                ),
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "connect_timeout": 23,
                "duration": ("fixed", (93780.0, 183840.0)),
            },
            ActiveCheckCommand(
                service_description="Mail Loop MailLoop_imap",
                command_arguments=[
                    "--fetch-protocol=IMAP",
                    "--fetch-server=imap.gmx.de",
                    "--fetch-tls",
                    "--fetch-username",
                    "me@gmx.de",
                    "--fetch-password-reference",
                    Secret(2),
                    "--connect-timeout=23",
                    "--send-protocol=SMTP",
                    "--send-server=smtp.gmx.de",
                    "--send-port=42",
                    "--send-tls",
                    "--send-username",
                    "me@gmx.de",
                    "--send-password-reference",
                    Secret(1),
                    "--mail-from=me_from@gmx.de",
                    "--mail-to=me_to@gmx.de",
                    "--status-suffix=non-existent-testhost-MailLoop_imap",
                    "--warning=93780",
                    "--critical=183840",
                    "--subject=Some subject",
                ],
            ),
        ),
        pytest.param(
            {
                "item": "foo",
                "send": (
                    "EWS",
                    {
                        "server": "$HOSTADDRESS$",
                        "connection": {
                            "disable_tls": False,
                            "disable_cert_validation": True,
                            "port": 50,
                        },
                        "auth": (
                            "oauth2",
                            {
                                "client_id": "client_id",
                                "client_secret": Secret(3),
                                "tenant_id": "tenant_id",
                            },
                        ),
                        "email_address": "address@email.com",
                    },
                ),
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", {"username": "hans", "password": Secret(4)}),
                    },
                ),
                "mail_from": "None",
                "mail_to": "None",
            },
            ActiveCheckCommand(
                service_description="Mail Loop foo",
                command_arguments=[
                    "--fetch-protocol=IMAP",
                    "--fetch-server=bar",
                    "--fetch-port=143",
                    "--fetch-username",
                    "hans",
                    "--fetch-password-reference",
                    Secret(4),
                    "--send-protocol=EWS",
                    "--send-server=5.6.7.8",
                    "--send-port=50",
                    "--send-tls",
                    "--send-disable-cert-validation",
                    "--send-client-id",
                    "client_id",
                    "--send-client-secret-reference",
                    Secret(3),
                    "--send-tenant-id",
                    "tenant_id",
                    "--send-email-address=address@email.com",
                    "--mail-from=None",
                    "--mail-to=None",
                    "--status-suffix=non-existent-testhost-foo",
                ],
            ),
            id="send EWS, OAuth",
        ),
        pytest.param(
            {
                "item": "foo",
                "send": (
                    "EWS",
                    {
                        "server": "$HOSTADDRESS$",
                        "connection": {
                            "disable_tls": False,
                            "disable_cert_validation": True,
                            "port": 50,
                        },
                        "auth": ("basic", {"username": "user", "password": Secret(5)}),
                        "email_address": "address@email.com",
                    },
                ),
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", {"username": "hans", "password": Secret(6)}),
                    },
                ),
                "mail_from": "None",
                "mail_to": "None",
                "delete_messages": True,
            },
            ActiveCheckCommand(
                service_description="Mail Loop foo",
                command_arguments=[
                    "--fetch-protocol=IMAP",
                    "--fetch-server=bar",
                    "--fetch-port=143",
                    "--fetch-username",
                    "hans",
                    "--fetch-password-reference",
                    Secret(6),
                    "--send-protocol=EWS",
                    "--send-server=5.6.7.8",
                    "--send-port=50",
                    "--send-tls",
                    "--send-disable-cert-validation",
                    "--send-username",
                    "user",
                    "--send-password-reference",
                    Secret(5),
                    "--send-email-address=address@email.com",
                    "--mail-from=None",
                    "--mail-to=None",
                    "--delete-messages",
                    "--status-suffix=non-existent-testhost-foo",
                ],
            ),
            id="send EWS, basic auth",
        ),
    ],
)
def test_check_mail_loop_argument_parsing(
    params: Mapping[str, object], expected_args: ActiveCheckCommand
) -> None:
    """Tests if all required arguments are present."""
    (actual,) = active_check_mail_loop(params, HOST_CONFIG)
    assert actual == expected_args
