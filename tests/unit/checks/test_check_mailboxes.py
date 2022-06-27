#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "fetch": (
                    "IMAP",
                    {
                        "server": "foo",
                        "connection": {
                            "disable_tls": True,
                            "tcp_port": 143,
                        },
                        "auth": ("hans", "wurst"),
                    },
                )
            },
            [
                "--fetch-protocol=IMAP",
                "--fetch-server=foo",
                "--fetch-port=143",
                "--fetch-username=hans",
                "--fetch-password=wurst",
            ],
        ),
        (
            {
                "fetch": (
                    "EWS",
                    {
                        "server": "foo",
                        "connection": {},
                        "auth": ("hans", "wurst"),
                    },
                )
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=foo",
                "--fetch-tls",
                "--fetch-username=hans",
                "--fetch-password=wurst",
            ],
        ),
    ],
)
def test_check_mailboxes_argument_parsing(params, expected_args) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mailboxes")
    assert active_check.run_argument_function(params) == expected_args
