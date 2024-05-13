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
        (
            {
                "item": "foo",
                "send": ("SMTP", {"connection": {}}),
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
                "--send-protocol=SMTP",
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
                "--fetch-password=p4ssw0rd",
                "--connect-timeout=23",
                "--send-protocol=SMTP",
                "--send-server=smtp.gmx.de",
                "--send-port=42",
                "--send-tls",
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
                "--send-protocol=EWS",
                "--send-server=$HOSTADDRESS$",
                "--send-port=50",
                "--send-tls",
                "--send-disable-cert-validation",
                "--send-client-id=client_id",
                ("store", "password_1", "--send-client-secret=%s"),
                "--send-tenant-id=tenant_id",
                "--send-email-address=address@email.com",
                "--mail-from=None",
                "--mail-to=None",
                "--status-suffix=non-existent-testhost-foo",
            ],
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
                        "auth": ("basic", ("hans", "wurst")),
                    },
                ),
                "mail_from": None,
                "mail_to": None,
                "delete_messages": True,
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=bar",
                "--fetch-port=143",
                "--fetch-username=hans",
                "--fetch-password=wurst",
                "--send-protocol=EWS",
                "--send-server=$HOSTADDRESS$",
                "--send-port=50",
                "--send-tls",
                "--send-disable-cert-validation",
                "--send-username=user",
                ("store", "password_1", "--send-password=%s"),
                "--send-email-address=address@email.com",
                "--mail-from=None",
                "--mail-to=None",
                "--delete-messages",
                "--status-suffix=non-existent-testhost-foo",
            ],
            id="send EWS, basic auth",
        ),
    ],
)
def test_check_mail_loop_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mail_loop")
    assert active_check.run_argument_function(params) == expected_args
