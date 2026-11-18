#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Graph,
    HostName,
    Line,
    MetricName,
    MinimalRange,
    RRDMetric,
    ServiceName,
    Unit,
)
from cmk.gui.graphing import BuiltGraph
from cmk.gui.graphing.openapi.models import ApiMinimalRange, ApiYAxis
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.utils.temperature_unit import TemperatureUnit

_RRD = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("s"), metric_name=MetricName("m")
)


def _built_graph(vertical_range: MinimalRange) -> BuiltGraph:
    unit = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))
    return BuiltGraph(
        graph=Graph(
            name="mygraph",
            title="My Graph",
            kind="template",
            vertical_range=vertical_range,
            lines=[
                Line(
                    curve=Curve(
                        quantity=_RRD,
                        attributes=CurveAttributes(title="l", unit=unit, color="#l"),
                    ),
                    inverse=False,
                )
            ],
        ),
        specification=None,
    )


def test_the_axis_carries_a_minimal_range() -> None:
    y_axis = ApiYAxis.from_built(
        _built_graph(MinimalRange(lower=0.0, upper=100.0)), TemperatureUnit.CELSIUS
    )
    assert y_axis is not None
    assert y_axis.vertical_range == ApiMinimalRange(type="minimal", min=0.0, max=100.0)


def test_the_axis_leaves_out_a_minimal_bound_only_the_data_resolves() -> None:
    y_axis = ApiYAxis.from_built(
        _built_graph(MinimalRange(lower=0.0, upper=_RRD)), TemperatureUnit.CELSIUS
    )
    assert y_axis is not None
    assert y_axis.vertical_range == ApiMinimalRange(type="minimal", min=0.0, max=ApiOmitted())
