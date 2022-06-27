#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

from cmk.base.core_config import HostAddressConfiguration

pytestmark = pytest.mark.checks

HOST_CONFIG = HostAddressConfiguration(
    hostname="hostname",
    host_address="0.0.0.1",
    alias="host_alias",
    ipv4address="0.0.0.2",
    ipv6address="0.0.0.3",
    indexed_ipv4addresses={"$_HOSTADDRESSES_4_1$": "0.0.0.4", "$_HOSTADDRESSES_4_2$": "0.0.0.5"},
    indexed_ipv6addresses={
        "$_HOSTADDRESSES_6_1$": "0.0.0.6",
        "$_HOSTADDRESSES_6_2$": "0.0.0.7",
        "$_HOSTADDRESSES_6_3$": "0.0.0.8",
    },
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"timeout": 30},
            [("PING", "-t 30 -w 200.00,80% -c 500.00,100% $HOSTADDRESS$")],
            id="timeout",
        ),
        pytest.param(
            {"address": "alias"},
            [("PING", "-w 200.00,80% -c 500.00,100% $HOSTALIAS$")],
            id="alias",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1")},
            [("PING IPv4/1", "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_1$")],
            id="indexed ipv4 address",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3")},
            [("PING IPv6/3", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_3$")],
            id="indexed ipv6 address",
        ),
        pytest.param(
            {"address": "all_ipv4addresses"},
            [
                (
                    "PING all IPv4 Addresses",
                    "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4$ $_HOSTADDRESS_4$",
                )
            ],
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "all_ipv6addresses"},
            [
                (
                    "PING all IPv6 Addresses",
                    "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6$ $_HOSTADDRESS_6$",
                )
            ],
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv4addresses"},
            [("PING", "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4$")],
            id="additional ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses"},
            [("PING", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6$")],
            id="additional ipv6 addresses",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address")},
            [("PING", "-w 200.00,80% -c 500.00,100% my.custom.address")],
            id="explicit address",
        ),
        pytest.param(
            {"timeout": 30, "multiple_services": True},
            [("PING 0.0.0.1", "-t 30 -w 200.00,80% -c 500.00,100% $HOSTADDRESS$")],
            id="timeout multiple services",
        ),
        pytest.param(
            {"address": "alias", "multiple_services": True},
            [("PING host_alias", "-w 200.00,80% -c 500.00,100% $HOSTALIAS$")],
            id="alias multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1"), "multiple_services": True},
            [("PING 0.0.0.4", "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_1$")],
            id="indexed ipv4 address multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3"), "multiple_services": True},
            [("PING 0.0.0.8", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_3$")],
            id="indexed ipv6 address multiple services",
        ),
        pytest.param(
            {"address": "all_ipv4addresses", "multiple_services": True},
            [
                (
                    "PING 0.0.0.4",
                    "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_1$",
                ),
                (
                    "PING 0.0.0.5",
                    "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_2$",
                ),
                (
                    "PING 0.0.0.2",
                    "-w 200.00,80% -c 500.00,100% $_HOSTADDRESS_4$",
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "all_ipv6addresses", "multiple_services": True},
            [
                (
                    "PING 0.0.0.6",
                    "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_1$",
                ),
                (
                    "PING 0.0.0.7",
                    "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_2$",
                ),
                (
                    "PING 0.0.0.8",
                    "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_3$",
                ),
                (
                    "PING 0.0.0.3",
                    "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESS_6$",
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv4addresses", "multiple_services": True},
            [
                ("PING 0.0.0.4", "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_1$"),
                ("PING 0.0.0.5", "-w 200.00,80% -c 500.00,100% $_HOSTADDRESSES_4_2$"),
            ],
            id="additional ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses", "multiple_services": True},
            [
                ("PING 0.0.0.6", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_1$"),
                ("PING 0.0.0.7", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_2$"),
                ("PING 0.0.0.8", "-w 200.00,80% -c 500.00,100% -6 $_HOSTADDRESSES_6_3$"),
            ],
            id="additional ipv6 addresses multiple services",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address"), "multiple_services": True},
            [("PING my.custom.address", "-w 200.00,80% -c 500.00,100% my.custom.address")],
            id="explicit address multiple services",
        ),
    ],
)
def test_generate_icmp_services(params, expected_result) -> None:
    active_check = ActiveCheck("check_icmp")
    services = list(active_check.run_generate_icmp_services(HOST_CONFIG, params))
    assert services == expected_result
