#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import math
from collections.abc import Callable, Mapping

import pytest

from cmk.agent_based.legacy.v0_unstable import _do_check_levels, check_levels, LegacyResult


def _rmeter(x: float | int) -> str:
    return "%.1f m" % x


def _rint(x: float | int) -> str:
    return str(int(x))


@pytest.mark.parametrize(
    "value, levels, representation, result",
    [
        (5, (3, 6), _rint, (1, " (warn/crit at 3/6)")),
        (7, (3, 6), _rmeter, (2, " (warn/crit at 3.0 m/6.0 m)")),
        (2, (3, 6, 1, 0), _rint, (0, "")),
        (1, (3, 6, 1, 0), _rint, (0, "")),
        (0, (3, 6, 1, 0), _rint, (1, " (warn/crit below 1/0)")),
        (-1, (3, 6, 1, 0), _rint, (2, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(
    value: int,
    levels: tuple[int, int, int, int],
    representation: Callable[[object], object],
    result: tuple[int, str],
) -> None:
    assert _do_check_levels(value, levels, representation) == result


@pytest.mark.parametrize(
    "value, dsname, params, kwargs, result",
    [
        (
            6,
            "disk",
            (4, 8),
            {"unit": "years", "infoname": "Disk Age"},
            (1, "Disk Age: 6.00 years (warn/crit at 4.00 years/8.00 years)", [("disk", 6.0, 4, 8)]),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 (warn/crit at pH 6.4/pH 6.1)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "unit": "??",
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 ?? (warn/crit at pH 6.4 ??/pH 6.1 ??)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
    ],
)
def test_check_levels(
    value: float,
    dsname: str | None,
    params: None | tuple[float, ...],
    kwargs: Mapping[str, object],
    result: LegacyResult,
) -> None:
    assert check_levels(value, dsname, params, **kwargs) == result  # type: ignore[arg-type]
