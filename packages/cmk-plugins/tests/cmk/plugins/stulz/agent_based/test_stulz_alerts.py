#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc,import-untyped"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.stulz.agent_based.stulz_alerts import (
    check_stulz_alerts,
    discover_stulz_alerts,
    parse_stulz_alerts,
)

_STRING_TABLE: list[list[str]] = [
    ["1010.1.1.1", "0"],
    ["1010.1.2.1", "2"],
]


def test_discover_stulz_alerts() -> None:
    parsed = parse_stulz_alerts(_STRING_TABLE)
    assert list(discover_stulz_alerts(parsed)) == [
        Service(item="1010.1.1.1"),
        Service(item="1010.1.2.1"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        ("1010.1.1.1", [Result(state=State.OK, summary="No alerts on device")]),
        ("1010.1.2.1", [Result(state=State.CRIT, summary="Device is in alert state")]),
        ("does-not-exist", []),
    ],
)
def test_check_stulz_alerts(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_stulz_alerts(_STRING_TABLE)
    assert list(check_stulz_alerts(item, parsed)) == expected_results
