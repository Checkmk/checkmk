#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.plugins.wato.active_checks_mailbox import transform_check_mail_params


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
                        "connection": {},
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
                        "connection": {},
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
                        "connection": {},
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
                        "connection": {},
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            id="no `server` element",
        ),
        pytest.param(
            {
                "service_description": "SD3",
                "fetch": (
                    "POP3",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                        "ssl": (False, 110),
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
            {
                "service_description": "SD3",
                "fetch": (
                    "POP3",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                        "connection": {"disable_tls": True, "port": 110},
                    },
                ),
                "connect_timeout": 12,
                "forward": {"match_subject": "test"},
            },
        ),
    ],
)
def test_transform_check_mail_params(old_rule, expected):
    assert transform_check_mail_params(old_rule) == expected
