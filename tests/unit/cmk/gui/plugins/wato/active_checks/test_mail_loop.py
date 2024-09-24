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
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("usr_imap", ("password", "pw_imap")),
                        "connection": {},
                    },
                ),
                "send": ("SMTP", {"connection": {}}),
            },
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {},
                    },
                ),
                "send": ("SMTP", {"connection": {}}),
            },
            id="old `auth` element",
        ),
        pytest.param(
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {"disable_tls": False, "tcp_port": 143},
                    },
                ),
                "send": ("SMTP", {"connection": {}}),
            },
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {
                            "disable_tls": False,
                            "port": 143,
                        },  # new param name "port"
                    },
                ),
                "send": ("SMTP", {"connection": {}}),
            },
            id="old param name 'tcp_port'",
        ),
        pytest.param(
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {},
                    },
                ),
                "smtp_auth": ("usr_smtp", ("password", "pw_smtp")),
                "smtp_port": 25,
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
            },
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {},
                    },
                ),
                "send": (
                    "SMTP",
                    {
                        "server": "smtp.gmx.de",
                        "auth": ("usr_smtp", ("password", "pw_smtp")),
                        "connection": {"tls": True, "port": 25},
                    },
                ),
            },
            id="old SMTP sending config",
        ),
    ],
)
def test_migrate_check_mail_loop_params(old_rule, expected):
    assert migrate_check_mail_loop_params(old_rule) == expected
