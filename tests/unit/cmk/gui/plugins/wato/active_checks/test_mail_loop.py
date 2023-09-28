#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.plugins.wato.active_checks.mailbox import migrate_check_mail_loop_params


@pytest.mark.parametrize(
    "old_rule,expected",
    [
        pytest.param(
            {
                "item": "service_name",
                "subject": "Some subject",
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "connect_timeout": 23,
                "smtp_auth": ("usr_smtp", ("password", "pw_smtp")),
                "duration": (93780, 183840),
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("usr_imap", ("password", "pw_imap")),
                        "connection": {"disable_tls": False, "tcp_port": 143},
                        "server": "imap.gmx.net",
                    },
                ),
                "smtp_port": 25,
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
            },
            {
                "item": "service_name",
                "subject": "Some subject",
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "connect_timeout": 23,
                "smtp_auth": ("usr_smtp", ("password", "pw_smtp")),
                "duration": (93780, 183840),
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {"disable_tls": False, "tcp_port": 143},
                        "server": "imap.gmx.net",
                    },
                ),
                "smtp_port": 25,
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
            },
            id="old `auth` element",
        ),
        pytest.param(
            {
                "item": "service_name",
                "subject": "Some subject",
                "connect_timeout": 23,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("foobar", ("password", "password")),
                        "connection": {},
                    },
                ),
            },
            {
                "item": "service_name",
                "subject": "Some subject",
                "connect_timeout": 23,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("foobar", ("password", "password"))),
                        "connection": {},
                    },
                ),
            },
            id="no `server` element",
        ),
    ],
)
def test_migrate_check_mail_loop_params(old_rule, expected):
    assert migrate_check_mail_loop_params(old_rule) == expected
