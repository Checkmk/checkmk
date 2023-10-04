#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks import check_dns


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {
                "hostname": "DESCR",
                "server": None,
            },
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L"],
        ),
        (
            {
                "hostname": "DESCR",
                "server": None,
                "expected_addresses_list": ["1.2.3.4", "5.6.7.8"],
            },
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L", "-a", "1.2.3.4", "-a", "5.6.7.8"],
        ),
        (
            {
                "hostname": "DESCR",
                "server": None,
                "expect_all_addresses": True,
                "expected_addresses_list": ["5.6.7.8", "1.2.3.4"],
            },
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-L", "-a", "5.6.7.8", "-a", "1.2.3.4"],
        ),
        (
            {
                "hostname": "DESCR",
                "server": None,
                "expect_all_addresses": False,
                "expected_addresses_list": ["1.2.3.4", "5.6.7.8"],
            },
            ["-H", "DESCR", "-s", "$HOSTADDRESS$", "-a", "1.2.3.4", "-a", "5.6.7.8"],
        ),
        (
            {
                "hostname": "google.de",
                "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
                "server": "127.0.0.53",
                "timeout": 10,
                "response_time": (1.0, 2.0),
                "expected_authority": True,
            },
            [
                "-H",
                "google.de",
                "-s",
                "127.0.0.53",
                "-L",
                "-a",
                "1.2.3.4",
                "-a",
                "C0FE::FE11",
                "-A",
                "-w",
                "1.000000",
                "-c",
                "2.000000",
                "-t",
                10,
            ],
        ),
    ],
)
def test_ac_check_dns_expected_addresses(
    params: Mapping[str, object], result: Sequence[object]
) -> None:
    assert check_dns.check_dns_arguments(params) == result
