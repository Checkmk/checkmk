#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import math

import pytest

from cmk.base.api.agent_based import render, utils
from cmk.base.api.agent_based.checking_classes import Metric, Result, State


@pytest.mark.parametrize(
    "value, levels_upper, levels_lower, render_func, result",
    [
        (5, (3, 6), None, int, (State.WARN, " (warn/crit at 3/6)")),
        (7, (3, 6), None, lambda x: "%.1f m" % x, (State.CRIT, " (warn/crit at 3.0 m/6.0 m)")),
        (7, (3, 6), None, lambda x: "%.1f" % x, (State.CRIT, " (warn/crit at 3.0/6.0)")),
        (2, (3, 6), (1, 0), int, (State.OK, "")),
        (1, (3, 6), (1, 0), int, (State.OK, "")),
        (0, (3, 6), (1, 0), int, (State.WARN, " (warn/crit below 1/0)")),
        (-1, (3, 6), (1, 0), int, (State.CRIT, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(value, levels_upper, levels_lower, render_func, result) -> None:
    assert utils._do_check_levels(value, levels_upper, levels_lower, render_func) == result


@pytest.mark.parametrize(
    "value, kwargs, result",
    [
        (
            5,
            {
                "metric_name": "battery",
                "render_func": render.percent,
            },
            [
                Result(state=State.OK, summary="5.00%"),
                Metric("battery", 5.0),
            ],
        ),
        (
            6,
            {
                "metric_name": "disk",
                "levels_upper": (4, 8),
                "render_func": lambda x: "%.2f years" % x,
                "label": "Disk Age",
            },
            [
                Result(
                    state=State.WARN,
                    summary="Disk Age: 6.00 years (warn/crit at 4.00 years/8.00 years)",
                ),
                Metric("disk", 6.0, levels=(4.0, 8.0)),
            ],
        ),
        (
            5e-7,
            {
                "metric_name": "H_concentration",
                "levels_upper": (4e-7, 8e-7),
                "levels_lower": (5e-8, 2e-8),
                "render_func": lambda x: "pH %.1f" % -math.log10(x),
                "label": "Water acidity",
                "boundaries": (0, None),
            },
            [
                Result(
                    state=State.WARN, summary="Water acidity: pH 6.3 (warn/crit at pH 6.4/pH 6.1)"
                ),
                Metric("H_concentration", 5e-7, levels=(4e-7, 8e-7), boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_levels(value, kwargs, result) -> None:
    assert list(utils.check_levels(value, **kwargs)) == result
