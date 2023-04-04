#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.plugins.wato.active_checks.mailbox import migrate_check_mail_params


@pytest.mark.parametrize(
    "old_rule,expected",
    [
        pytest.param(
            {
                "service_description": "SD1",
                "fetch": (
                    "IMAP",
                    {
                        "server": "srv",
                        "auth": ("usr", ("password", "pw")),
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            {
                "service_description": "SD1",
                "fetch": (
                    "IMAP",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            id="old `auth` element",
        ),
        pytest.param(
            {
                "service_description": "SD2",
                "fetch": (
                    "POP3",
                    {
                        "auth": ("basic", ("usr", ("password", "pw"))),
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            {
                "service_description": "SD2",
                "fetch": (
                    "POP3",
                    {
                        "auth": ("basic", ("usr", ("password", "pw"))),
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            id="no `server` element",
        ),
    ],
)
def test_migrate_check_mail_params(old_rule, expected):
    assert migrate_check_mail_params(old_rule) == expected
