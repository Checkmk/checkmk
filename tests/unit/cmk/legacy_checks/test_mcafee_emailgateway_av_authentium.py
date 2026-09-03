#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.mcafee_emailgateway_av_authentium import (
    check_mcafee_emailgateway_av_authentium,
    discover_mcafee_emailgateway_av_authentium,
)


@pytest.mark.parametrize(
    "activated, expected_services",
    [
        ("1", [Service()]),
        ("0", []),
    ],
)
def test_discover(activated: str, expected_services: list[Service]) -> None:
    section: StringTable = [[activated, "5", "100"]]
    assert list(discover_mcafee_emailgateway_av_authentium(section)) == expected_services


@pytest.mark.parametrize(
    "activated, expected_state, expected_status",
    [
        ("1", State.OK, "activated"),
        ("0", State.WARN, "deactivated"),
        ("7", State.UNKNOWN, "unknown[7]"),
    ],
)
def test_check(activated: str, expected_state: State, expected_status: str) -> None:
    section: StringTable = [[activated, "5", "100"]]
    assert list(check_mcafee_emailgateway_av_authentium(section)) == [
        Result(
            state=expected_state,
            summary=f"Status: {expected_status}, Engine version: 5, DAT version: 100",
        )
    ]
