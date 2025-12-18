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
from cmk.plugins.fast_lta.agent_based.fast_lta_headunit import (
    check_fast_lta_headunit_replication,
    inventory_fast_lta_headunit_replication,
)


@pytest.mark.parametrize("info, expected", [([["60", "1", "1"]], [Service()])])
def test_discovery_fast_lta_headunit_replication(
    info: Sequence[StringTable],
    expected: DiscoveryResult,
) -> None:
    assert list(inventory_fast_lta_headunit_replication(info)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [[["60", "1", "1"]]],
            [Result(state=State.OK, summary="Replication is running. This node is Master.")],
        ),
        (
            [[["60", "1", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). This node is Master.",
                )
            ],
        ),
        (
            [[["60", "255", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). This node is standalone.",
                )
            ],
        ),
        (
            [[["60", "88", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). Replication mode of this node is 88.",
                )
            ],
        ),
    ],
)
def test_check_fast_lta_headunit_replication(
    info: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    assert list(check_fast_lta_headunit_replication(info)) == expected
