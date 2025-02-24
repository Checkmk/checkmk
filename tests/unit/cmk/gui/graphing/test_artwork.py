#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.gui.graphing._artwork import (
    _areastack,
    _compute_graph_t_axis,
    _compute_v_axis_min_max,
    _halfstep_interpolation,
    _t_axis_labels_seconds,
    _t_axis_labels_week,
    _VAxisMinMax,
    Curve,
    LayoutedCurve,
    LayoutedCurveLine,
    LayoutedCurveStack,
    order_graph_curves_for_legend_and_mouse_hover,
    TimeAxis,
    TimeAxisLabel,
)
from cmk.gui.graphing._graph_specification import FixedVerticalRange, MinimalVerticalRange
from cmk.gui.graphing._utils import SizeEx
from cmk.gui.time_series import TimeSeries, TimeSeriesValue, Timestamp


@pytest.mark.parametrize(
    "explicit_vertical_range, layouted_curves, graph_data_vrange, mirrored, expected_v_axis_min_max",
    [
        pytest.param(
            None,
            [],
            None,
            False,
            _VAxisMinMax(1.0, (0.0, 1.5)),
            id="default",
        ),
        pytest.param(
            None,
            [],
            None,
            True,
            _VAxisMinMax(2.0, (-2.0, 2.0)),
            id="default-mirrored",
        ),
        #
        pytest.param(
            MinimalVerticalRange(min=0.01, max=0.02),
            [],
            None,
            False,
            _VAxisMinMax(0.01, (0.005, 0.025)),
            id="small-pos",
        ),
        pytest.param(
            FixedVerticalRange(min=0.01, max=0.02),
            [],
            None,
            True,
            _VAxisMinMax(0.04, (-0.04, 0.04)),
            id="small-pos-mirrored",
        ),
        pytest.param(
            MinimalVerticalRange(min=-0.01, max=0.02),
            [],
            None,
            False,
            _VAxisMinMax(0.03, (-0.025, 0.035)),
            id="small-neg",
        ),
        pytest.param(
            FixedVerticalRange(min=-0.01, max=0.02),
            [],
            None,
            True,
            _VAxisMinMax(0.04, (-0.04, 0.04)),
            id="small-neg-mirrored",
        ),
        #
        pytest.param(
            MinimalVerticalRange(min=-5.0, max=10.0),
            [],
            None,
            False,
            _VAxisMinMax(15.0, (-12.5, 17.5)),
            id="explicit_vertical_range",
        ),
        pytest.param(
            FixedVerticalRange(min=-5.0, max=10.0),
            [],
            None,
            True,
            _VAxisMinMax(20.0, (-20.0, 20.0)),
            id="explicit_vertical_range-mirrored",
        ),
        pytest.param(
            None,
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-5.0, 10.0],
                )
            ],
            None,
            False,
            _VAxisMinMax(15.0, (-12.5, 17.5)),
            id="layouted_curves",
        ),
        pytest.param(
            None,
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-5.0, 10.0],
                )
            ],
            None,
            True,
            _VAxisMinMax(20.0, (-20.0, 20.0)),
            id="layouted_curves-mirrored",
        ),
        pytest.param(
            None,
            [],
            (-5.0, 10.0),
            False,
            _VAxisMinMax(15.0, (-5.0, 10.0)),
            id="graph_data_vrange",
        ),
        pytest.param(
            None,
            [],
            (-5.0, 10.0),
            True,
            _VAxisMinMax(20.0, (-10.0, 10.0)),
            id="graph_data_vrange-mirrored",
        ),
    ],
)
def test__compute_v_axis_min_max(
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    layouted_curves: Sequence[LayoutedCurve],
    graph_data_vrange: tuple[float, float] | None,
    mirrored: bool,
    expected_v_axis_min_max: _VAxisMinMax,
) -> None:
    assert (
        _compute_v_axis_min_max(
            explicit_vertical_range,
            layouted_curves,
            graph_data_vrange,
            mirrored,
            SizeEx(1),
        )
        == expected_v_axis_min_max
    )


@pytest.mark.parametrize(
    "explicit_vertical_range, layouted_curves, graph_data_vrange, expected_v_axis_min_max",
    [
        pytest.param(
            FixedVerticalRange(min=-500.0, max=1000.0),
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-600.0, 2000.0],
                )
            ],
            None,
            _VAxisMinMax(1500.0, (-1250.0, 1750.0)),
            id="explicit_vertical_range_fixed-and-layouted_curves",
        ),
        pytest.param(
            MinimalVerticalRange(min=-500.0, max=1000.0),
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-250.0, 500.0],
                )
            ],
            None,
            _VAxisMinMax(1500.0, (-1250.0, 1750.0)),
            id="explicit_vertical_range_minimal-and-layouted_curves_smaller",
        ),
        pytest.param(
            MinimalVerticalRange(min=-500.0, max=1000.0),
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-1000.0, 2000.0],
                )
            ],
            None,
            _VAxisMinMax(3000.0, (-2500.0, 3500.0)),
            id="explicit_vertical_range_minimal-and-layouted_curves_larger",
        ),
        pytest.param(
            None,
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[1000.0, 2000.0],
                )
            ],
            None,
            _VAxisMinMax(2000.0, (0, 3000.0)),
            id="layouted_curves_at_least_zero",
        ),
        pytest.param(
            FixedVerticalRange(min=-500.0, max=1000.0),
            [],
            (-5.0, 10.0),
            _VAxisMinMax(15.0, (-5.0, 10.0)),
            id="graph_data_vrange-precedence-over-explicit_vertical_range",
        ),
        pytest.param(
            None,
            [
                LayoutedCurveLine(
                    color="",
                    title="",
                    scalars={},
                    type="line",
                    points=[-500.0, 1000.0],
                )
            ],
            (-5.0, 10.0),
            _VAxisMinMax(15.0, (-5.0, 10.0)),
            id="graph_data_vrange-precedence-over-layouted_curves",
        ),
    ],
)
def test__compute_v_axis_min_max_precedence(
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    layouted_curves: Sequence[LayoutedCurve],
    graph_data_vrange: tuple[float, float] | None,
    expected_v_axis_min_max: _VAxisMinMax,
) -> None:
    assert (
        _compute_v_axis_min_max(
            explicit_vertical_range,
            layouted_curves,
            graph_data_vrange,
            False,
            SizeEx(1),
        )
        == expected_v_axis_min_max
    )


def test_t_axis_labels_seconds() -> None:
    with time_machine.travel(datetime(2024, 1, 1, tzinfo=ZoneInfo("Europe/Berlin"))):
        assert [
            label_pos.timestamp()
            for label_pos in _t_axis_labels_seconds(
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
    with time_machine.travel(datetime(2024, 1, 1, tzinfo=ZoneInfo("Europe/Berlin"))):
        assert [
            label_pos.timestamp()
            for label_pos in _t_axis_labels_week(
                datetime.fromtimestamp(1565401600),
                datetime.fromtimestamp(1566691200),
            )
        ] == [
            1565560800.0,
            1566165600.0,
        ]


def test_halfstep_interpolation() -> None:
    assert _halfstep_interpolation(TimeSeries([5.0, 7.0, None], (123, 234, 10))) == [
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
    assert _areastack(args[1], args[0]) == result


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
                    TimeAxisLabel(
                        position=1668502800.0,
                        text="10:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668504000.0,
                        text="10:20",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668505200.0,
                        text="10:40",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668506400.0,
                        text="11:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668507600.0,
                        text="11:20",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668508800.0,
                        text="11:40",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668510000.0,
                        text="12:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668511200.0,
                        text="12:20",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668512400.0,
                        text="12:40",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668513600.0,
                        text="13:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668514800.0,
                        text="13:20",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668516000.0,
                        text="13:40",
                        line_width=2,
                    ),
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
                    TimeAxisLabel(
                        position=1668438000.0,
                        text="Mon 16:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668452400.0,
                        text="Mon 20:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668466800.0,
                        text="Tue 00:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668481200.0,
                        text="Tue 04:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668495600.0,
                        text="Tue 08:00",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668510000.0,
                        text="Tue 12:00",
                        line_width=2,
                    ),
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
                    TimeAxisLabel(
                        position=1667862000.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1667905200.0,
                        text="08",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1667948400.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1667991600.0,
                        text="09",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668034800.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668078000.0,
                        text="10",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668121200.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668164400.0,
                        text="11",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668207600.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668250800.0,
                        text="12",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668294000.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668337200.0,
                        text="13",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668380400.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668423600.0,
                        text="14",
                        line_width=0,
                    ),
                    TimeAxisLabel(
                        position=1668466800.0,
                        text=None,
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668510000.0,
                        text=None,
                        line_width=0,
                    ),
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
                    TimeAxisLabel(
                        position=1665698400.0,
                        text="10-14",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1665957600.0,
                        text="10-17",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1666216800.0,
                        text="10-20",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1666476000.0,
                        text="10-23",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1666735200.0,
                        text="10-26",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1666994400.0,
                        text="10-29",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1667257200.0,
                        text="11-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1667516400.0,
                        text="11-04",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1667775600.0,
                        text="11-07",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668034800.0,
                        text="11-10",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1668294000.0,
                        text="11-13",
                        line_width=2,
                    ),
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
                    TimeAxisLabel(
                        position=1638313200.0,
                        text="2021-12-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1643670000.0,
                        text="2022-02-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1648764000.0,
                        text="2022-04-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1654034400.0,
                        text="2022-06-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1659304800.0,
                        text="2022-08-01",
                        line_width=2,
                    ),
                    TimeAxisLabel(
                        position=1664575200.0,
                        text="2022-10-01",
                        line_width=2,
                    ),
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
    step: int,
    expected_result: TimeAxis,
) -> None:
    with time_machine.travel(datetime(2024, 1, 1, tzinfo=ZoneInfo("Europe/Berlin"))):
        assert (
            _compute_graph_t_axis(
                start_time=start_time,
                end_time=end_time,
                width=width,
                step=step,
            )
            == expected_result
        )


def test_order_graph_curves_for_legend_and_mouse_hover_curves() -> None:
    rrd_data = TimeSeries([1.0, 2.0, 1.0])
    assert list(
        order_graph_curves_for_legend_and_mouse_hover(
            [
                Curve(
                    line_type="line",
                    color="",
                    title="1",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="ref",
                    color="",
                    title="2",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="-area",
                    color="",
                    title="3",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="stack",
                    color="",
                    title="4",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="area",
                    color="",
                    title="5",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="-stack",
                    color="",
                    title="6",
                    rrddata=rrd_data,
                ),
                Curve(
                    line_type="stack",
                    color="",
                    title="7",
                    rrddata=rrd_data,
                ),
            ]
        )
    ) == [
        Curve(
            line_type="line",
            color="",
            title="1",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="ref",
            color="",
            title="2",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="-area",
            color="",
            title="3",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="stack",
            color="",
            title="7",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="area",
            color="",
            title="5",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="-stack",
            color="",
            title="6",
            rrddata=rrd_data,
        ),
        Curve(
            line_type="stack",
            color="",
            title="4",
            rrddata=rrd_data,
        ),
    ]


def test_order_graph_curves_for_legend_and_mouse_hover_layouted_curves() -> None:
    layouted_curves: list[LayoutedCurve] = [
        LayoutedCurveStack(
            type="stack",
            color="",
            title="1",
            scalars={},
            points=[],
        ),
        LayoutedCurveStack(
            type="stack",
            color="",
            title="2",
            scalars={},
            points=[],
        ),
        LayoutedCurveLine(
            type="line",
            color="",
            title="3",
            scalars={},
            points=[],
        ),
    ]
    assert list(order_graph_curves_for_legend_and_mouse_hover(layouted_curves)) == [
        LayoutedCurveStack(
            type="stack",
            color="",
            title="2",
            scalars={},
            points=[],
        ),
        LayoutedCurveStack(
            type="stack",
            color="",
            title="1",
            scalars={},
            points=[],
        ),
        LayoutedCurveLine(
            type="line",
            color="",
            title="3",
            scalars={},
            points=[],
        ),
    ]
