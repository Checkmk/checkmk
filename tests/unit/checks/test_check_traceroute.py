#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
                "dns": False,
                "routers": [],
                "method": "",
                "address_family": "ipv4",
            },
            ["-n", "-4", "$HOSTADDRESS$"],
        ),
        (
            {
                "dns": True,
                "routers": [],
                "method": "",
                "address_family": "ipv4",
            },
            ["-4", "$HOSTADDRESS$"],
        ),
        (
            {
                "dns": True,
                "routers": [("127.0.0.1", "WARN")],
                "method": "icmp",
                "address_family": "ipv4",
            },
            ["-I", "-WARN", "127.0.0.1", "-4", "$HOSTADDRESS$"],
        ),
        (
            {
                "dns": False,
                "routers": [],
                "method": "",
                "address_family": "ipv4",
            },
            ["-n", "-4", "$HOSTADDRESS$"],
        ),
        (
            {
                "dns": False,
                "routers": [],
                "method": "",
                "address_family": "ipv6",
            },
            ["-n", "-6", "$HOSTADDRESS$"],
        ),
    ],
)
def test_check_traceroute_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_traceroute")
    assert active_check.run_argument_function(params) == expected_args
