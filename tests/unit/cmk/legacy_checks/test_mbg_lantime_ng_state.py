#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks.mbg_lantime_ng_state import (
    check_mbg_lantime_ng_state,
    parse_mbg_lantime_ng_state,
)
from cmk.plugins.meinberg.liblantime import MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS


@pytest.mark.parametrize(
    "params, expected_results",
    [
        (
            {
                "stratum": (2, 3),
                "offset": (10, 20),  # us
            },
            [
                Result(state=State.OK, summary="State: synchronized"),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Reference clock: GPS"),
                Result(state=State.OK, summary="Reference clock offset: 0.9 µs"),
                Metric("offset", 0.9, levels=(10.0, 20.0)),
            ],
        ),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 20),  # us
            },
            [
                Result(state=State.OK, summary="State: synchronized"),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Reference clock: GPS"),
                Result(
                    state=State.WARN,
                    summary="Reference clock offset: 0.9 µs (warn/crit at 0.9 µs/20 µs)",
                ),
                Metric("offset", 0.9, levels=(0.9, 20.0)),
            ],
        ),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 0.9),  # us
            },
            [
                Result(state=State.OK, summary="State: synchronized"),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Reference clock: GPS"),
                Result(
                    state=State.CRIT,
                    summary="Reference clock offset: 0.9 µs (warn/crit at 0.9 µs/0.9 µs)",
                ),
                Metric("offset", 0.9, levels=(0.9, 0.9)),
            ],
        ),
    ],
)
def test_mbg_lantime_ng_state_ref_clock(
    params: Mapping[str, tuple[float, float]], expected_results: Sequence[object]
) -> None:
    assert (
        list(
            check_mbg_lantime_ng_state(
                params, parse_mbg_lantime_ng_state([["2", "1", "GPS", "0.0009"]])
            )
        )
        == expected_results
    )


def test_parsing_with_equal_sign_wont_crash() -> None:
    assert list(
        check_mbg_lantime_ng_state(
            MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
            parse_mbg_lantime_ng_state([["0", "2", "=NAME", "=0.1234"]]),
        )
    ) == [
        Result(state=State.CRIT, summary="State: not available"),
        Result(state=State.WARN, summary="Stratum: 2 (warn/crit at 2/3)"),
        Result(state=State.OK, summary="Reference clock: NAME"),
        Result(
            state=State.CRIT,
            summary="Reference clock offset: 123.4 µs (warn/crit at 10 µs/20 µs)",
        ),
        Metric("offset", 123.39999999999999, levels=(10.0, 20.0)),
    ]
