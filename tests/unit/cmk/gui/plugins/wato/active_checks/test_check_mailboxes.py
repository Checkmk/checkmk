#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.plugins.wato.active_checks_mailbox import transform_check_mailbox_params


@pytest.mark.parametrize(
    "old_rule,expected",
    [
        pytest.param(
            {
                "service_description": "SD1",
                "fetch": (
                    "EWS",
                    {
                        "server": "srv",
                        "auth": ("usr", ("password", "pw")),
                        "connection": {},
                    },
                ),
                "age": (1, 2),
                "age_newest": (3, 4),
                "count": (5, 6),
                "mailboxes": ["abc", "def"],
            },
            {
                "service_description": "SD1",
                "fetch": (
                    "EWS",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                        "connection": {},
                    },
                ),
                "age": (1, 2),
                "age_newest": (3, 4),
                "count": (5, 6),
                "mailboxes": ["abc", "def"],
            },
            id="old `auth` element",
        ),
        pytest.param(
            {
                "service_description": "SD1",
                "fetch": (
                    "EWS",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                        "connection": {
                            "disable_tls": False,
                            "disable_cert_validation": False,
                            "tcp_port": 123,
                        },
                    },
                ),
            },
            {
                "service_description": "SD1",
                "fetch": (
                    "EWS",
                    {
                        "server": "srv",
                        "auth": ("basic", ("usr", ("password", "pw"))),
                        "connection": {
                            "disable_tls": False,
                            "disable_cert_validation": False,
                            "port": 123,  # new param name "port"
                        },
                    },
                ),
            },
            id="old param name 'tcp_port'",
        ),
    ],
)
def test_transform_check_mailboxes_params(old_rule, expected):
    assert transform_check_mailbox_params(old_rule) == expected
