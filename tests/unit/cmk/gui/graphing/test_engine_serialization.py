#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence

from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Difference,
    EngineeringScientificNotation,
    FixedRange,
    Fraction,
    Graph,
    IECNotation,
    Line,
    MetricName,
    MinimalRange,
    Product,
    RRDMetric,
    Rule,
    ScalarOf,
    ScalarType,
    SINotation,
    Stack,
    StandardScientificNotation,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing._engine_serialization import (
    deserialize_graphs,
    serialize_graphs,
)

_METRIC = RRDMetric(host_name="h", service_name="svc", metric_name=MetricName("m"))
_METRIC_CF = RRDMetric(
    host_name="h",
    service_name="svc",
    metric_name=MetricName("m2"),
    consolidation_function=ConsolidationFunction.MAX,
)


_Notation = (
    DecimalNotation
    | SINotation
    | IECNotation
    | StandardScientificNotation
    | EngineeringScientificNotation
    | TimeNotation
)
_Precision = AutoPrecision | StrictPrecision


def _attributes(notation: _Notation, precision: _Precision) -> CurveAttributes:
    return CurveAttributes(
        title="t", unit=Unit(notation=notation, precision=precision), color="#abcdef"
    )


def _rich_graphs() -> Sequence[Graph]:
    # One graph exercising every engine quantity, vertical range and a value-type spread. Discovery
    # resolves display, so every curve carries its own CurveAttributes alongside the quantity.
    decimal = _attributes(DecimalNotation(symbol="B"), AutoPrecision(digits=2))
    scientific = _attributes(StandardScientificNotation(symbol=""), StrictPrecision(digits=3))
    si = _attributes(SINotation(symbol="W"), AutoPrecision(digits=1))
    iec = _attributes(IECNotation(symbol="B"), StrictPrecision(digits=0))
    time = _attributes(TimeNotation(symbol="s"), AutoPrecision(digits=2))
    engineering = _attributes(EngineeringScientificNotation(symbol=""), AutoPrecision(digits=2))
    return [
        Graph(
            name="g1",
            title="G1",
            graph_type="template",
            vertical_range=FixedRange(lower=0, upper=100),
            stacks=[
                Stack(
                    members=[
                        Curve(quantity=_METRIC, attributes=decimal),
                        Curve(quantity=Sum([_METRIC, _METRIC_CF], decimal), attributes=decimal),
                    ],
                    inverse=True,
                    reference=Curve(quantity=Constant(5, scientific), attributes=scientific),
                )
            ],
            lines=[
                Line(
                    curve=Curve(
                        quantity=Fraction(dividend=_METRIC, divisor=Constant(2), display=decimal),
                        attributes=decimal,
                    ),
                    inverse=False,
                ),
                Line(
                    curve=Curve(
                        quantity=Product([_METRIC, Constant(3.5)], display=None),
                        attributes=scientific,
                    ),
                    inverse=True,
                ),
            ],
            rules=[
                Rule(
                    curve=Curve(
                        quantity=ScalarOf(metric=_METRIC, scalar_type=ScalarType.WARNING),
                        attributes=si,
                    ),
                    inverse=False,
                ),
                Rule(
                    curve=Curve(
                        quantity=ScalarOf(
                            metric=_METRIC, scalar_type=ScalarType.MAXIMUM, color="#00ff00"
                        ),
                        attributes=iec,
                    ),
                    inverse=False,
                ),
            ],
        ),
        Graph(
            name="g2",
            title="G2",
            graph_type="template",
            # A Bound that is itself a quantity, plus the remaining notation / precision variants.
            vertical_range=MinimalRange(lower=Constant(0), upper=_METRIC),
            lines=[
                Line(
                    curve=Curve(
                        quantity=Difference(minuend=_METRIC, subtrahend=_METRIC_CF, display=si),
                        attributes=si,
                    ),
                    inverse=False,
                ),
                Line(
                    curve=Curve(quantity=Sum([_METRIC], iec), attributes=iec),
                    inverse=False,
                ),
                Line(
                    curve=Curve(quantity=Constant(1, time), attributes=time),
                    inverse=False,
                ),
                Line(
                    curve=Curve(quantity=Constant(2, engineering), attributes=engineering),
                    inverse=False,
                ),
            ],
        ),
    ]


def test_template_round_trip_is_lossless() -> None:
    built_graphs = _rich_graphs()
    payload = serialize_graphs(built_graphs)
    # The payload is plain JSON.
    assert json.loads(json.dumps(payload)) == payload
    # Each graph carries its own graph_type; there is no separate envelope field.
    serialized_graphs = payload["graphs"]
    assert isinstance(serialized_graphs, list)
    assert all(graph["graph_type"] == "template" for graph in serialized_graphs)
    # The round-trip is stable: deserializing and re-serializing reproduces the same payload (compared
    # as JSON, so the empty-sequence list/tuple distinction the dataclass defaults carry is irrelevant).
    assert serialize_graphs(deserialize_graphs(payload)) == payload
