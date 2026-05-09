#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+---------------------------------------------------------+
|              Achtung Alles Lookenskeepers!              |
|              =============================              |
|                                                         |
| The extend of the Check API is well documented, and the |
| result of careful negotiation. It should not be changed |
| light heartedly!                                        |
+---------------------------------------------------------+
"""

import pytest

from cmk.graphing import v2_unstable


@pytest.mark.parametrize(
    "filename, expected_result",
    [
        (
            None,
            {
                "entry_point_prefixes",
                "graphs",
                "metrics",
                "perfometers",
                "translations",
                "Title",
            },
        ),
        (
            "metrics",
            {
                "AutoPrecision",
                "Color",
                "Constant",
                "CriticalOf",
                "DecimalNotation",
                "Difference",
                "EngineeringScientificNotation",
                "Fraction",
                "IECNotation",
                "LowerCriticalOf",
                "LowerWarningOf",
                "MaximumOf",
                "Metric",
                "MinimumOf",
                "Product",
                "SINotation",
                "StandardScientificNotation",
                "StrictPrecision",
                "Sum",
                "TimeNotation",
                "Unit",
                "WarningOf",
            },
        ),
    ],
)
def test_v2_unstable(filename: str | None, expected_result: set[str]) -> None:
    if not filename:
        assert set(v2_unstable.__all__) == expected_result
        return
    assert set(getattr(v2_unstable, filename).__all__) == expected_result
