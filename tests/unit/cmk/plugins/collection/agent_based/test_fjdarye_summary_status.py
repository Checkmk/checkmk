#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_summary_status import (
    check_fjdarye_sum,
    discover_fjdarye_sum,
    FjdaryeDeviceStatus,
    parse_fjdarye_sum,
)


@pytest.mark.parametrize(
    "section, parse_sum_result",
    [
        pytest.param(
            [
                [["3"]],
                [],
                [],
            ],
            FjdaryeDeviceStatus("3"),
            id="If the length of the section is 1, a Mapping containing the status is parsed.",
        ),
        pytest.param(
            [
                [
                    ["3", "1"],
                ],
                [],
                [],
            ],
            None,
            id="If the length of the section is more than 1, nothing in parsed",
        ),
        pytest.param(
            [],
            None,
            id="If the section is empty, nothing is parsed",
        ),
    ],
)
def test_parse_fjdarye_sum(
    section: Sequence[StringTable],
    parse_sum_result: FjdaryeDeviceStatus | None,
) -> None:
    assert parse_fjdarye_sum(section) == parse_sum_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        # Assumption: The input will always be a FjdaryeDeviceStatus, because it's the output of the parse_fjdarye_sum function,
        pytest.param(
            FjdaryeDeviceStatus("3"),
            [Service()],
            id="If the length of the section is 1, a service with no further information is returned",
        ),
        pytest.param(
            None,
            [],
            id="If the section is None, no services are discovered",
        ),
    ],
)
def test_discover_fjdarye_sum(
    section: FjdaryeDeviceStatus | None,
    discovery_result: DiscoveryResult,
) -> None:
    assert list(discover_fjdarye_sum(section)) == discovery_result


@pytest.mark.parametrize(
    "section, check_sum_result",
    [
        pytest.param(
            None,
            [],
            id="If the input is None, the check result is an empty list, which leads to the state going to UNKNOWN",
        ),
        pytest.param(
            FjdaryeDeviceStatus("3"),
            [Result(state=State.OK, summary="Status: ok")],
            id="If the summary status is equal to 3, the check result state is OK",
        ),
        pytest.param(
            FjdaryeDeviceStatus("4"),
            [Result(state=State.WARN, summary="Status: warning")],
            id="If the summary status is equal 4, the check result state is WARN",
        ),
        pytest.param(
            FjdaryeDeviceStatus("5"),
            [Result(state=State.CRIT, summary="Status: failed")],
            id="If the summary status is 1 or 2 or 5, the check result state is WARN and the description is the corresponding value from the fjdarye_sum_status mapping",
        ),
        pytest.param(
            FjdaryeDeviceStatus("6"),
            [Result(state=State.UNKNOWN, summary="Status: unknown")],
            id="If the summary status not known, the check result is UNKNOWN.",
        ),
    ],
)
def test_check_fjdarye_sum(
    section: FjdaryeDeviceStatus | None,
    check_sum_result: CheckResult,
) -> None:
    assert list(check_fjdarye_sum(section=section)) == check_sum_result
