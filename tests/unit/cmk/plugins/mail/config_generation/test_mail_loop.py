#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.config_generation.v1 import HostConfig, IPAddressFamily, PlainTextSecret, StoredSecret
from cmk.plugins.mail.config_generation.mail_loop import active_check_mail_loop

HOST_CONFIG = HostConfig(
    name="host",
    address="127.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
)


@pytest.mark.parametrize(
    "params,expected_args, expected_desc",
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
                        "auth": ("basic", ("hans", ("password", "wurst"))),
                    },
                ),
                "mail_from": "",
                "mail_to": "",
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                PlainTextSecret(value="wurst", format="--fetch-password=%s"),
                "--send-protocol=SMTP",
                "--send-server=127.0.0.1",
                "--mail-from=",
                "--mail-to=",
                "--status-suffix=host-foo",
            ],
            "Mail Loop foo",
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
                        "auth": ("me@gmx.de", ("password", "p4ssw0rd")),
                    },
                ),
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
                PlainTextSecret(value="p4ssw0rd", format="--fetch-password=%s"),
                "--connect-timeout=23",
                "--send-protocol=SMTP",
                "--send-server=smtp.gmx.de",
                "--send-port=42",
                "--send-tls",
                "--send-username=me@gmx.de",
                PlainTextSecret(value="p4ssw0rd", format="--send-password=%s"),
                "--mail-from=me_from@gmx.de",
                "--mail-to=me_to@gmx.de",
                "--status-suffix=host-MailLoop_imap",
                "--warning=93780",
                "--critical=183840",
                "--subject=Some subject",
            ],
            "Mail Loop MailLoop_imap",
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
                        "auth": ("oauth2", ("client_id", ("store", "password_1"), "tenant_id")),
                        "email_address": "address@email.com",
                    },
                ),
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", ("hans", ("password", "wurst"))),
                    },
                ),
                "mail_from": "",
                "mail_to": "",
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                PlainTextSecret(value="wurst", format="--fetch-password=%s"),
                "--send-protocol=EWS",
                "--send-server=127.0.0.1",
                "--send-port=50",
                "--send-tls",
                "--send-disable-cert-validation",
                "--send-client-id=client_id",
                StoredSecret(value="password_1", format="--send-client-secret=%s"),
                "--send-tenant-id=tenant_id",
                "--send-email-address=address@email.com",
                "--mail-from=",
                "--mail-to=",
                "--status-suffix=host-foo",
            ],
            "Mail Loop foo",
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
                        "auth": ("basic", ("user", ("store", "password_1"))),
                        "email_address": "address@email.com",
                    },
                ),
                "fetch": (
                    "IMAP",
                    {
                        "server": "bar",
                        "connection": {"disable_tls": True, "port": 143},
                        "auth": ("basic", ("hans", ("password", "wurst"))),
                    },
                ),
                "mail_from": "",
                "mail_to": "",
                "delete_messages": True,
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                PlainTextSecret(value="wurst", format="--fetch-password=%s"),
                "--send-protocol=EWS",
                "--send-server=127.0.0.1",
                "--send-port=50",
                "--send-tls",
                "--send-disable-cert-validation",
                "--send-username=user",
                StoredSecret(value="password_1", format="--send-password=%s"),
                "--send-email-address=address@email.com",
                "--mail-from=",
                "--mail-to=",
                "--delete-messages",
                "--status-suffix=host-foo",
            ],
            "Mail Loop foo",
            id="send EWS, basic auth",
        ),
    ],
)
def test_check_mail_loop_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str], expected_desc: str
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = active_check_mail_loop.parameter_parser(params)
    commands = list(active_check_mail_loop.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
    assert commands[0].service_description == expected_desc
