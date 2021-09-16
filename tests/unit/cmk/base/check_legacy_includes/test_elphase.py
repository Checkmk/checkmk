#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Tuple

import pytest

from cmk.base.check_legacy_includes.elphase import check_elphase  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        pytest.param(
            "Output",
            {},
            {
                "Output": {
                    "voltage": 231.0,
                    "current": 10.0,
                    "output_load": 4.0,
                },
            },
            [
                (
                    0,
                    "Voltage: 231.0 V",
                    [("voltage", 231.0, None, None)],
                ),
                (
                    0,
                    "Current: 10.0 A",
                    [("current", 10.0, None, None)],
                ),
                (
                    0,
                    "Load: 4.0%",
                    [("output_load", 4.0, None, None)],
                ),
            ],
            id="no parameters",
        ),
        pytest.param(
            "Output",
            {
                "voltage": (250, 200),
                "output_load": (0, 2),
            },
            {
                "Output": {
                    "voltage": 231.0,
                    "current": 10.0,
                    "output_load": 4.0,
                },
            },
            [
                (
                    1,
                    "Voltage: 231.0 V (warn/crit below 250.0 V/200.0 V)",
                    [("voltage", 231.0, None, None)],
                ),
                (
                    0,
                    "Current: 10.0 A",
                    [("current", 10.0, None, None)],
                ),
                (
                    2,
                    "Load: 4.0% (warn/crit at 0%/2.0%)",
                    [("output_load", 4.0, 0, 2)],
                ),
            ],
            id="with parameters",
        ),
        pytest.param(
            "Output",
            {
                "current": (10, 15),
                "differential_current_ac": (90, 100),
            },
            {
                "Output": {
                    "current": 10.0,
                    "differential_current_ac": 100,
                },
            },
            [
                (
                    1,
                    "Current: 10.0 A (warn/crit at 10.0 A/15.0 A)",
                    [("current", 10.0, 10.0, 15.0)],
                ),
                (
                    2,
                    "Differential current AC: 100.0 mA (warn/crit at 90.0 mA/100.0 mA)",
                    [("differential_current_ac", 0.1, 0.09, 0.1)],
                ),
            ],
            id="with parameters, value exactly at the threshold",
        ),
    ],
)
def test_check_elphase(
    item: str,
    params: Mapping[str, Any],
    parsed: Mapping[str, Mapping[str, float]],
    expected_result: Sequence[Tuple],
) -> None:
    assert (
        list(
            check_elphase(
                item,
                params,
                parsed,
            )
        )
        == expected_result
    )
