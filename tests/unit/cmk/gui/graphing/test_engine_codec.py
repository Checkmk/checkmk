#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence

import pytest

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
    HostName,
    IECNotation,
    Line,
    MetricName,
    MinimalRange,
    Product,
    QuantityProtocol,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceName,
    SINotation,
    SiteID,
    Stack,
    StandardScientificNotation,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing._engine_codec import (
    community_graph_codec,
    COMMUNITY_QUANTITY_SPECS,
    graph_codec,
    QuantitySpec,
)

_METRIC = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("m")
)
_METRIC_CF = RRDMetric(
    host_name=HostName("h"),
    service_name=ServiceName("svc"),
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
            kind="template",
            vertical_range=FixedRange(lower=0, upper=100),
            stacks=[
                Stack(
                    members=[
                        Curve(quantity=_METRIC, attributes=decimal, source_id="A"),
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
                        quantity=ScalarOf(metric=_METRIC, scalar_kind=ScalarKind.WARNING),
                        attributes=si,
                    ),
                    inverse=False,
                ),
                Rule(
                    curve=Curve(
                        quantity=ScalarOf(
                            metric=_METRIC, scalar_kind=ScalarKind.MAXIMUM, color="#00ff00"
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
            kind="template",
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


def test_rrd_metric_site_id_round_trips() -> None:
    # A resolved site must survive the self-contained graph JSON, so a same host/service on two sites
    # stays distinct after a round-trip.
    metric = RRDMetric(
        site_id=SiteID("mysite"),
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=MetricName("m"),
    )
    attributes = CurveAttributes(
        title="t",
        unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
        color="#abcdef",
    )
    graph = Graph(
        name="g",
        title="G",
        kind="template",
        lines=[Line(curve=Curve(quantity=metric, attributes=attributes), inverse=False)],
    )
    codec = community_graph_codec()
    [restored] = codec.deserialize_graphs(codec.serialize_graphs([graph]))
    [line] = restored.lines
    assert line.curve.quantity == metric


def test_omit_zero_curves_round_trips() -> None:
    # The option rides on the graph, not on the request, so losing it here would silently drop it
    # for every graph rendered from the posted wire form.
    graph = Graph(name="g", title="G", kind="custom", omit_zero_curves=True)
    codec = community_graph_codec()
    [restored] = codec.deserialize_graphs(codec.serialize_graphs([graph]))
    assert restored.omit_zero_curves is True


def test_template_round_trip_is_lossless() -> None:
    codec = community_graph_codec()
    graphs = _rich_graphs()
    payload = codec.serialize_graphs(graphs)
    # The payload is plain JSON.
    assert json.loads(json.dumps(payload)) == payload
    # Each graph carries its own kind; there is no separate envelope field.
    serialized_graphs = payload["graphs"]
    assert isinstance(serialized_graphs, list)
    assert all(graph["kind"] == "template" for graph in serialized_graphs)
    # The round-trip is stable: deserializing and re-serializing reproduces the same payload (compared
    # as JSON, so the empty-sequence list/tuple distinction the dataclass defaults carry is irrelevant).
    restored = codec.deserialize_graphs(payload)
    assert codec.serialize_graphs(restored) == payload
    # The source id survives the round-trip; untagged curves stay untagged.
    assert restored[0].stacks[0].members[0].source_id == "A"
    assert restored[0].stacks[0].members[1].source_id is None


_ROUND_TRIP_METRIC = RRDMetric(
    site_id=SiteID("mysite"),
    host_name=HostName("h"),
    service_name=ServiceName("svc"),
    metric_name=MetricName("m"),
    consolidation_function=ConsolidationFunction.MIN,
)
_ROUND_TRIP_DISPLAY = CurveAttributes(
    title="display",
    unit=Unit(notation=IECNotation("B"), precision=StrictPrecision(3)),
    color="#010203",
)
# One sample per quantity kind the engine codec registers, with EVERY field set to a non-default
# value: a field dropped from either direction of the codec comes back as its default and fails the
# equality assertion. test_every_engine_quantity_kind_is_covered keeps this in step with the codec.
_ENGINE_QUANTITY_SAMPLES: Mapping[str, QuantityProtocol] = {
    "rrd_metric": _ROUND_TRIP_METRIC,
    "constant": Constant(23.5, _ROUND_TRIP_DISPLAY),
    "scalar_of": ScalarOf(
        metric=_ROUND_TRIP_METRIC, scalar_kind=ScalarKind.LOWER_CRITICAL, color="#040506"
    ),
    "sum": Sum([_ROUND_TRIP_METRIC, Constant(1.0)], _ROUND_TRIP_DISPLAY),
    "product": Product([_ROUND_TRIP_METRIC, Constant(2.0)], _ROUND_TRIP_DISPLAY),
    "difference": Difference(
        minuend=_ROUND_TRIP_METRIC, subtrahend=Constant(3.0), display=_ROUND_TRIP_DISPLAY
    ),
    "fraction": Fraction(
        dividend=_ROUND_TRIP_METRIC, divisor=Constant(4.0), display=_ROUND_TRIP_DISPLAY
    ),
}


@pytest.mark.parametrize("kind", sorted(_ENGINE_QUANTITY_SAMPLES))
def test_engine_quantity_round_trips_every_field(kind: str) -> None:
    quantity = _ENGINE_QUANTITY_SAMPLES[kind]
    codec = community_graph_codec()
    serialized = json.loads(json.dumps(codec.serialize_quantity(quantity)))
    assert serialized["kind"] == kind
    assert codec.deserialize_quantity(serialized) == quantity


def test_every_engine_quantity_kind_is_covered() -> None:
    # The engine stays de/serialization-free, so a quantity's fields are mirrored by hand in the
    # codec. A new quantity kind must arrive with a round-trip sample above, or this fails.
    assert set(_ENGINE_QUANTITY_SAMPLES) == set(community_graph_codec().quantity_kinds())


def test_a_codec_refuses_two_quantities_claiming_one_kind() -> None:
    duplicate = QuantitySpec(
        "constant",
        lambda quantity, codec: {},
        lambda data, codec: Constant(0.0),
    )
    with pytest.raises(ValueError, match="duplicate quantity kind: constant"):
        graph_codec((*COMMUNITY_QUANTITY_SPECS, duplicate))
