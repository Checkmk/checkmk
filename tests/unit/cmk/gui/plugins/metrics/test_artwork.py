#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.gui.plugins.metrics import artwork


@pytest.mark.parametrize(
    "_min, _max, mirrored, result",
    [
        (5, 15, False, (5, 15)),
        (None, None, False, (0, 1)),
        (None, None, True, (-1, 1)),
        (None, 5, False, (0, 5)),
        (None, 5, True, (-5, 5)),
    ],
)
def test_min(_min, _max, mirrored, result):
    assert artwork._purge_min_max(_min, _max, mirrored) == result


@pytest.mark.parametrize(
    "args, result",
    [
        (
            (1565481600, 1565481620, 10, 5),
            [
                (1565481600.0, 2, True),
                (1565481605.0, 0, False),
                (1565481610.0, 2, True),
                (1565481615.0, 0, False),
                (1565481620.0, 2, True),
            ],
        ),
    ],
)
def test_dist_equal(args, result):
    with on_time("2019-09-09", "Europe/Berlin"):
        assert list(artwork.dist_equal(*args)) == result


@pytest.mark.parametrize(
    "args, result",
    [
        (
            (1565401600, 1566691200),
            [
                (1565474400.0, 0, False),
                (1565560800.0, 2, True),
                (1565647200.0, 0, False),
                (1565733600.0, 0, False),
                (1565820000.0, 0, False),
                (1565906400.0, 0, False),
                (1565992800.0, 0, False),
                (1566079200.0, 0, False),
                (1566165600.0, 2, True),
                (1566252000.0, 0, False),
                (1566338400.0, 0, False),
                (1566424800.0, 0, False),
                (1566511200.0, 0, False),
                (1566597600.0, 0, False),
                (1566684000.0, 0, False),
            ],
        ),
    ],
)
def test_dist_week(args, result):
    with on_time("2019-09-09", "Europe/Berlin"):
        assert list(artwork.dist_week(*args)) == result


def test_halfstep_interpolation():
    assert artwork.halfstep_interpolation([5, 7, None]) == [5, 5, 5, 6, 7, 7, None]


@pytest.mark.parametrize(
    "args, result",
    [
        pytest.param(([], list(range(3))), [(0, 0), (0, 1), (0, 2)], id="area"),
        pytest.param(([], [5, None, 6]), [(0, 5), (None, None), (0, 6)], id="area holes"),
        pytest.param(([0, 0], [1, 2]), [(0, 1), (0, 2)], id="stack"),
        pytest.param(([0, 1], [1, 1]), [(0, 1), (1, 2)], id="stack"),
        pytest.param(([None, 0], [1, 2]), [(0, 1), (0, 2)], id="stack on holes"),
        pytest.param(([None, 0], [None, 2]), [(None, None), (0, 2)], id="stack data missing"),
        pytest.param(([], [-1, -2, -0.5]), [(-1, 0), (-2, 0), (-0.5, 0)], id="mirror area"),
        pytest.param(
            ([], [-5, None, -6]), [(-5, 0), (None, None), (-6, 0)], id="mirror area holes"
        ),
    ],
)
def test_fringe(args, result):
    assert artwork.areastack(args[1], args[0]) == result
