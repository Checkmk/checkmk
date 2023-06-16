#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime

import pytest

from tests.testlib import set_timezone

from cmk.utils.prediction import Seconds, TimeSeries, TimeSeriesValue, Timestamp

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
def test_min(
    _min: int | None,
    _max: int | None,
    mirrored: bool,
    result: tuple[int, int],
) -> None:
    assert artwork._purge_min_max(_min, _max, mirrored) == result


def test_t_axis_labels_seconds() -> None:
    with set_timezone("Europe/Berlin"):
        assert [
            label_pos.timestamp()
            for label_pos in artwork._t_axis_labels_seconds(
                datetime.fromtimestamp(1565481600),
                datetime.fromtimestamp(1565481620),
                10,
            )
        ] == [
            1565481600.0,
            1565481610.0,
            1565481620.0,
        ]


def test_t_axis_labels_week() -> None:
    with set_timezone("Europe/Berlin"):
        assert [
            label_pos.timestamp()
            for label_pos in artwork._t_axis_labels_week(
                datetime.fromtimestamp(1565401600),
                datetime.fromtimestamp(1566691200),
            )
        ] == [
            1565560800.0,
            1566165600.0,
        ]


def test_halfstep_interpolation() -> None:
    assert artwork.halfstep_interpolation(TimeSeries([5.0, 7.0, None], (123, 234, 10))) == [
        5.0,
        5.0,
        5.0,
        6.0,
        7.0,
        7.0,
        None,
    ]


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
def test_fringe(
    args: tuple[Sequence[TimeSeriesValue], Sequence[TimeSeriesValue]],
    result: Sequence[tuple[TimeSeriesValue, TimeSeriesValue]],
) -> None:
    assert artwork.areastack(args[1], args[0]) == result


@pytest.mark.parametrize(
    ["start_time", "end_time", "width", "step", "expected_result"],
    [
        pytest.param(
            1668502320,
            1668516720,
            70,
            60,
            {
                "labels": [
                    (1668502800.0, "10:00", 2),
                    (1668504000.0, "10:20", 2),
                    (1668505200.0, "10:40", 2),
                    (1668506400.0, "11:00", 2),
                    (1668507600.0, "11:20", 2),
                    (1668508800.0, "11:40", 2),
                    (1668510000.0, "12:00", 2),
                    (1668511200.0, "12:20", 2),
                    (1668512400.0, "12:40", 2),
                    (1668513600.0, "13:00", 2),
                    (1668514800.0, "13:20", 2),
                    (1668516000.0, "13:40", 2),
                ],
                "range": (1668502320, 1668516720),
                "title": "2022-11-15 @ 1m",
            },
            id="4h",
        ),
        pytest.param(
            1668426600,
            1668516600,
            70,
            300,
            {
                "labels": [
                    (1668438000.0, "Mon 16:00", 2),
                    (1668452400.0, "Mon 20:00", 2),
                    (1668466800.0, "Tue 00:00", 2),
                    (1668481200.0, "Tue 04:00", 2),
                    (1668495600.0, "Tue 08:00", 2),
                    (1668510000.0, "Tue 12:00", 2),
                ],
                "range": (1668426600, 1668516600),
                "title": "2022-11-14 — 2022-11-15 @ 5m",
            },
            id="25h",
        ),
        pytest.param(
            1667826000,
            1668517200,
            70,
            1800,
            {
                "labels": [
                    (1667862000.0, None, 2),
                    (1667905200.0, "08", 0),
                    (1667948400.0, None, 2),
                    (1667991600.0, "09", 0),
                    (1668034800.0, None, 2),
                    (1668078000.0, "10", 0),
                    (1668121200.0, None, 2),
                    (1668164400.0, "11", 0),
                    (1668207600.0, None, 2),
                    (1668250800.0, "12", 0),
                    (1668294000.0, None, 2),
                    (1668337200.0, "13", 0),
                    (1668380400.0, None, 2),
                    (1668423600.0, "14", 0),
                    (1668466800.0, None, 2),
                    (1668510000.0, None, 0),
                ],
                "range": (1667826000, 1668517200),
                "title": "2022-11-07 — 2022-11-15 @ 30m",
            },
            id="8d",
        ),
        pytest.param(
            1665486000,
            1668519000,
            70,
            9000,
            {
                "labels": [
                    (1665698400.0, "10-14", 2),
                    (1665957600.0, "10-17", 2),
                    (1666216800.0, "10-20", 2),
                    (1666476000.0, "10-23", 2),
                    (1666735200.0, "10-26", 2),
                    (1666994400.0, "10-29", 2),
                    (1667257200.0, "11-01", 2),
                    (1667516400.0, "11-04", 2),
                    (1667775600.0, "11-07", 2),
                    (1668034800.0, "11-10", 2),
                    (1668294000.0, "11-13", 2),
                ],
                "range": (1665486000, 1668519000),
                "title": "2022-10-11 — 2022-11-15 @ 2h",
            },
            id="35d",
        ),
        pytest.param(
            1633910400,
            1668470400,
            70,
            86400,
            {
                "labels": [
                    (1638313200.0, "2021-12-01", 2),
                    (1643670000.0, "2022-02-01", 2),
                    (1648764000.0, "2022-04-01", 2),
                    (1654034400.0, "2022-06-01", 2),
                    (1659304800.0, "2022-08-01", 2),
                    (1664575200.0, "2022-10-01", 2),
                ],
                "range": (1633910400, 1668470400),
                "title": "2021-10-12 — 2022-11-14 @ 1d",
            },
            id="400d",
        ),
    ],
)
def test_compute_graph_t_axis(
    start_time: Timestamp,
    end_time: Timestamp,
    width: int,
    step: Seconds,
    expected_result: artwork.TimeAxis,
) -> None:
    with set_timezone("Europe/Berlin"):
        assert (
            artwork.compute_graph_t_axis(
                start_time=start_time,
                end_time=end_time,
                width=width,
                step=step,
            )
            == expected_result
        )
