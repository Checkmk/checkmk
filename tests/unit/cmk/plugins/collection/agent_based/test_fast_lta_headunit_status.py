#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.base.legacy_checks.fast_lta_headunit import (
    check_fast_lta_headunit_status,
    inventory_fast_lta_headunit_status,
)


@pytest.mark.parametrize("info, expected", [([["60", "1", "1"]], [Service()])])
def test_discovery_fast_lta_headunit_status(
    info: Sequence[StringTable],
    expected: DiscoveryResult,
) -> None:
    assert list(inventory_fast_lta_headunit_status(info)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [[["60", "1", "1"]]],
            [Result(state=State.OK, summary="Head Unit status is appReady.")],
        ),
        (
            [[["75", "1", "1"]]],
            [Result(state=State.CRIT, summary="Head Unit status is appEnterpriseCubes.")],
        ),
        (
            [[["70", "0", "1"]]],
            [Result(state=State.OK, summary="Head Unit status is appReadOnly.")],
        ),
        (
            [[["99", "0", "1"]]],
            [Result(state=State.CRIT, summary="Head Unit status is 99.")],
        ),
    ],
)
def test_check_fast_lta_headunit_status(
    info: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    assert list(check_fast_lta_headunit_status(info)) == expected
