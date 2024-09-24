#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
import time_machine

from cmk.base.legacy_checks.jolokia_metrics import check_request_count

PARSED_SECTION = [
    ["myinstance,/manager", "requestCount", "3"],
    ["myinstance,/weblogic", "CompletedRequestCount", "10"],
]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "myinstance /manager",
            [(0, "3.00 requests/sec", [("rate", 3)])],
            id="requestCount present",
        ),
        pytest.param(
            "myinstance /notfound",
            [],
            id="requestCount not present",
        ),
        pytest.param(
            "myinstance /weblogic",
            [(0, "1.00 requests/sec", [("rate", 1.0)])],
            id="CompletedRequestCount rate",
        ),
    ],
)
def test_check_request_count(
    item: str,
    expected_result: list,
) -> None:
    value_store = {"j4p.bea.requests.myinstance /weblogic": (0, 0)}

    with time_machine.travel(10, tick=False):
        result = list(check_request_count(item, PARSED_SECTION, value_store))
        assert result == expected_result
