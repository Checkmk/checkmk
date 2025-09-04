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

from cmk.inventory_ui import v1_alpha


@pytest.mark.parametrize(
    "filename, expected_result",
    [
        (
            None,
            {
                "AgeNotation",
                "Alignment",
                "AutoPrecision",
                "BackgroundColor",
                "BoolField",
                "ChoiceField",
                "DecimalNotation",
                "EngineeringScientificNotation",
                "IECNotation",
                "Label",
                "LabelColor",
                "Node",
                "NumberField",
                "SINotation",
                "StandardScientificNotation",
                "StrictPrecision",
                "Table",
                "TextField",
                "TimeNotation",
                "Title",
                "Unit",
                "View",
                "entry_point_prefixes",
            },
        ),
    ],
)
def test_v1(filename: str | None, expected_result: set[str]) -> None:
    if not filename:
        assert set(v1_alpha.__all__) == expected_result
        return
    assert set(getattr(v1_alpha, filename).__all__) == expected_result
