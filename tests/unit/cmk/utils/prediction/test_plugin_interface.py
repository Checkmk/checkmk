#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Optional

import pytest

from cmk.utils.prediction import estimate_levels, EstimatedLevels


@pytest.mark.parametrize(
    "reference_value, reference_deviation, params, levels_factor, result",
    [
        (
            5,
            2,
            {"levels_lower": ("absolute", (2, 4))},
            1,
            (None, None, 3, 1),
        ),
        (
            15,
            2,
            {
                "levels_upper": ("stdev", (2, 4)),
                "levels_lower": ("stdev", (3, 5)),
            },
            1,
            (19, 23, 9, 5),
        ),
        (
            2,
            3,
            {
                "levels_upper": ("relative", (20, 40)),
                "levels_upper_min": (2, 4),
            },
            1,
            (2.4, 4, None, None),
        ),
        (
            None,
            object(),  # should never be used
            {},
            1,
            (None, None, None, None),
        ),
    ],
)
def test_estimate_levels(
    reference_value: Optional[float],
    reference_deviation: Optional[float],
    params: Mapping,
    levels_factor: float,
    result: EstimatedLevels,
) -> None:
    assert (
        estimate_levels(
            reference_value=reference_value,
            stdev=reference_deviation,
            levels_lower=params.get("levels_lower"),
            levels_upper=params.get("levels_upper"),
            levels_upper_lower_bound=params.get("levels_upper_min"),
            levels_factor=levels_factor,
        )
        == result
    )
