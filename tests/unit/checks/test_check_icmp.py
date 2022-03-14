#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {"timeout": 30},
            "-t 30 -w 200.00,80% -c 500.00,100% $HOSTADDRESS$",
            id="timeout",
        ),
        pytest.param(
            {"address": "all_ipv4addresses"},
            "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4$ $_HOSTADDRESS_4$",
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses"},
            "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6$",
            id="additional ipv6 addresses",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", 1)},
            "-w 200.00,80% -c 500.00,100% $_HOSTADDRESS_4_1$",
            id="indexed ipv4 address",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address")},
            "-w 200.00,80% -c 500.00,100% my.custom.address",
            id="explicit address",
        ),
    ],
)
def test_check_icmp_argument_parsing(
    params: Mapping[str, Any],
    expected_args: str,
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_icmp")
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize(
    "params, expected_description",
    [
        ({"address": ("indexed_ipv4address", "1")}, "PING IPv4/1"),
        ({"address": ("indexed_ipv6address", "3")}, "PING IPv6/3"),
        ({"address": "all_ipv4addresses"}, "PING all IPv4 Addresses"),
        ({"address": "all_ipv6addresses"}, "PING all IPv6 Addresses"),
    ],
)
def test_check_icmp_description(params, expected_description):
    active_check = ActiveCheck("check_icmp")
    assert active_check.run_service_description(params) == expected_description
