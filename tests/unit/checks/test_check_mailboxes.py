#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

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
                        "auth": ("basic", ("hans", "wurst")),
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
                        "auth": ("basic", ("hans", "wurst")),
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
        (
            {
                "fetch": (
                    "EWS",
                    {
                        "server": "foo",
                        "connection": {},
                        "auth": ("oauth2", ("client_id", "client_secret", "tenant_id")),
                    },
                )
            },
            [
                "--fetch-protocol=EWS",
                "--fetch-server=foo",
                "--fetch-tls",
                "--fetch-client-id=client_id",
                "--fetch-client-secret=client_secret",
                "--fetch-tenant-id=tenant_id",
            ],
        ),
    ],
)
def test_check_mailboxes_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mailboxes")
    assert active_check.run_argument_function(params) == expected_args
