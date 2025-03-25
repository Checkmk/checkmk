#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.check_legacy_includes.mbg_lantime import MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS
from cmk.base.legacy_checks.mbg_lantime_ng_state import (
    check_mbg_lantime_ng_state,
    parse_mbg_lantime_ng_state,
)

from .checktestlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {
                "stratum": (2, 3),
                "offset": (10, 20),  # us
            },
            (0, "Reference clock offset: 0.9 \xb5s", [("offset", 0.9, 10, 20)]),
        ),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 20),  # us
            },
            (
                1,
                "Reference clock offset: 0.9 \xb5s (warn/crit at 0.9 \xb5s/20 \xb5s)",
                [("offset", 0.9, 0.9, 20)],
            ),
        ),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 0.9),  # us
            },
            (
                2,
                "Reference clock offset: 0.9 \xb5s (warn/crit at 0.9 \xb5s/0.9 \xb5s)",
                [("offset", 0.9, 0.9, 0.9)],
            ),
        ),
    ],
)
def test_mbg_lantime_ng_state_ref_clock(
    params: Mapping[str, tuple[float, float]], result: tuple[float, str, Sequence[object]]
) -> None:
    check = Check("mbg_lantime_ng_state")
    ref_clock_result = list(check.run_check(None, params, [["2", "1", "GPS", "0.0009"]]))[-1]
    assert ref_clock_result == result


def test_parsing_with_equal_sign_wont_crash() -> None:
    assert list(
        check_mbg_lantime_ng_state(
            None,
            MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
            parse_mbg_lantime_ng_state([["0", "2", "=NAME", "=0.1234"]]),
        )
    ) == [
        (2, "State: not available", []),
        (1, "Stratum: 2 (warn/crit at 2/3)", []),
        (0, "Reference clock: NAME", []),
        (
            2,
            "Reference clock offset: 123.4 µs (warn/crit at 10 µs/20 µs)",
            [("offset", 123.39999999999999, 10, 20)],
        ),
    ]
