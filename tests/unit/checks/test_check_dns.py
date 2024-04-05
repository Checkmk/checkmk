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
            {"hostname": "foo", "server": None},
            ["-H", "foo", "-s", "$HOSTADDRESS$", "-L"],
        ),
        (
            {"hostname": "foo", "server": None, "timeout": 1},
            ["-H", "foo", "-s", "$HOSTADDRESS$", "-L", "-t", 1],
        ),
        (
            {
                "hostname": "foo",
                "server": "some_dns_server",
                "name": "check_name",
                "dns_server": "some_dns_server",
                "expected_addresses_list": ("2.4.5.6", "2.4.5.7"),
                "expected_authority": True,
                "response_time": (100.0, 200.0),
                "timeout": 10,
            },
            [
                "-H",
                "foo",
                "-s",
                "some_dns_server",
                "-L",
                "-a",
                "2.4.5.6",
                "-a",
                "2.4.5.7",
                "-A",
                "-w",
                "100.000000",
                "-c",
                "200.000000",
                "-t",
                10,
            ],
        ),
    ],
)
def test_check_dns_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_dns")
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize(
    "params, result",
    [
        [
            {"hostname": "google.de"},
            "DNS google.de",
        ],
        [
            {"hostname": "google.de", "name": "random_string"},
            "random_string",
        ],
    ],
)
def test_check_dns_desc(params: Mapping[str, object], result: str) -> None:
    active_check = ActiveCheck("check_dns")
    assert active_check.run_service_description(params) == result
