#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

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
    IECNotation,
    Line,
    MetricName,
    MinimalRange,
    Product,
    Quantity,
    ResolvedGraph,
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

_Json = dict[str, object]


def ensure_type[T](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return value


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"expected a mapping, got {type(value).__name__}")
    return value


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"expected a list, got {type(value).__name__}")
    return value


def _as_number(value: object) -> int | float:
    if not isinstance(value, int | float):
        raise TypeError(f"expected a number, got {type(value).__name__}")
    return value


# Quantity is an open protocol spanning packages, and the engine must stay serialization-free, so the
# codec is an external registry keyed by type (forward) and by tag (reverse). The engine layer
# registers its own quantities below; the pro layer composes its aggregation quantities on top.


@dataclass(frozen=True)
class QuantitySpec:
    tag: str
    cls: type
    to_dict: Callable[[Quantity, QuantityCodec], _Json]
    from_dict: Callable[[Mapping[str, object], QuantityCodec], Quantity]


class QuantityCodec:
    def __init__(self, specs: Sequence[QuantitySpec]) -> None:
        self._specs = tuple(specs)
        self._by_type = {spec.cls: spec for spec in self._specs}
        self._by_tag = {spec.tag: spec for spec in self._specs}

    def serialize(self, quantity: Quantity) -> _Json:
        spec = self._by_type[type(quantity)]
        return {"type": spec.tag, **spec.to_dict(quantity, self)}

    def deserialize(self, data: object) -> Quantity:
        data = _as_mapping(data)
        return self._by_tag[ensure_type(data["type"], str)].from_dict(data, self)


_NOTATIONS: Mapping[str, type] = {
    cls.__name__: cls
    for cls in (
        DecimalNotation,
        SINotation,
        IECNotation,
        StandardScientificNotation,
        EngineeringScientificNotation,
        TimeNotation,
    )
}

_PRECISIONS: Mapping[str, type] = {cls.__name__: cls for cls in (AutoPrecision, StrictPrecision)}


def _unit_to_json(unit: Unit) -> _Json:
    return {
        "notation": {"kind": type(unit.notation).__name__, "symbol": unit.notation.symbol},
        "precision": {"kind": type(unit.precision).__name__, "digits": unit.precision.digits},
    }


def _unit_from_json(data: object) -> Unit:
    data = _as_mapping(data)
    notation = _as_mapping(data["notation"])
    precision = _as_mapping(data["precision"])
    return Unit(
        notation=_NOTATIONS[ensure_type(notation["kind"], str)](
            symbol=ensure_type(notation["symbol"], str)
        ),
        precision=_PRECISIONS[ensure_type(precision["kind"], str)](
            digits=ensure_type(precision["digits"], int)
        ),
    )


def _attributes_to_json(attributes: CurveAttributes) -> _Json:
    return {
        "title": attributes.title,
        "unit": _unit_to_json(attributes.unit),
        "color": attributes.color,
    }


def _attributes_from_json(data: object) -> CurveAttributes:
    data = _as_mapping(data)
    return CurveAttributes(
        title=ensure_type(data["title"], str),
        unit=_unit_from_json(data["unit"]),
        color=ensure_type(data["color"], str),
    )


def display_to_json(display: CurveAttributes | None) -> _Json | None:
    return None if display is None else _attributes_to_json(display)


def display_from_json(data: object) -> CurveAttributes | None:
    return None if data is None else _attributes_from_json(data)


def _bound_to_json(bound: int | float | Quantity, codec: QuantityCodec) -> _Json:
    if isinstance(bound, int | float):
        return {"kind": "number", "value": bound}
    return {"kind": "quantity", "quantity": codec.serialize(bound)}


def _bound_from_json(data: object, codec: QuantityCodec) -> int | float | Quantity:
    data = _as_mapping(data)
    if data["kind"] == "number":
        return _as_number(data["value"])
    return codec.deserialize(data["quantity"])


def _range_to_json(vertical_range: MinimalRange | FixedRange, codec: QuantityCodec) -> _Json:
    return {
        "kind": "minimal" if isinstance(vertical_range, MinimalRange) else "fixed",
        "lower": _bound_to_json(vertical_range.lower, codec),
        "upper": _bound_to_json(vertical_range.upper, codec),
    }


def _range_from_json(data: object, codec: QuantityCodec) -> MinimalRange | FixedRange:
    data = _as_mapping(data)
    cls = MinimalRange if data["kind"] == "minimal" else FixedRange
    return cls(
        lower=_bound_from_json(data["lower"], codec), upper=_bound_from_json(data["upper"], codec)
    )


def _rrd_metric_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, RRDMetric)
    return {
        "host_name": quantity.host_name,
        "service_name": quantity.service_name,
        "metric_name": str(quantity.metric_name),
        "consolidation_function": (
            None
            if quantity.consolidation_function is None
            else str(quantity.consolidation_function)
        ),
    }


def _rrd_metric_from(data: Mapping[str, object], codec: QuantityCodec) -> RRDMetric:
    consolidation_function = data["consolidation_function"]
    return RRDMetric(
        host_name=ensure_type(data["host_name"], str),
        service_name=ensure_type(data["service_name"], str),
        metric_name=MetricName(ensure_type(data["metric_name"], str)),
        consolidation_function=(
            None
            if consolidation_function is None
            else ConsolidationFunction(ensure_type(consolidation_function, str))
        ),
    )


def _constant_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, Constant)
    return {"value": quantity.value, "display": display_to_json(quantity.display)}


def _constant_from(data: Mapping[str, object], codec: QuantityCodec) -> Constant:
    return Constant(_as_number(data["value"]), display_from_json(data["display"]))


def _scalar_of_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, ScalarOf)
    return {
        "metric": codec.serialize(quantity.metric),
        "scalar_type": str(quantity.scalar_type),
        "color": quantity.color,
    }


def _scalar_of_from(data: Mapping[str, object], codec: QuantityCodec) -> ScalarOf:
    color = data["color"]
    if color is not None and not isinstance(color, str):
        raise TypeError(f"expected a string or None, got {type(color).__name__}")
    return ScalarOf(
        metric=ensure_type(codec.deserialize(data["metric"]), RRDMetric),
        scalar_type=ScalarType(ensure_type(data["scalar_type"], str)),
        color=color,
    )


def _operands_to(operands: Sequence[Quantity], codec: QuantityCodec) -> list[_Json]:
    return [codec.serialize(operand) for operand in operands]


def operands_from(data: object, codec: QuantityCodec) -> list[Quantity]:
    return [codec.deserialize(operand) for operand in _as_list(data)]


def _sum_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, Sum)
    return {
        "summands": _operands_to(quantity.summands, codec),
        "display": display_to_json(quantity.display),
    }


def _sum_from(data: Mapping[str, object], codec: QuantityCodec) -> Sum:
    return Sum(operands_from(data["summands"], codec), display_from_json(data["display"]))


def _product_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, Product)
    return {
        "factors": _operands_to(quantity.factors, codec),
        "display": display_to_json(quantity.display),
    }


def _product_from(data: Mapping[str, object], codec: QuantityCodec) -> Product:
    return Product(operands_from(data["factors"], codec), display_from_json(data["display"]))


def _difference_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, Difference)
    return {
        "minuend": codec.serialize(quantity.minuend),
        "subtrahend": codec.serialize(quantity.subtrahend),
        "display": display_to_json(quantity.display),
    }


def _difference_from(data: Mapping[str, object], codec: QuantityCodec) -> Difference:
    return Difference(
        minuend=codec.deserialize(data["minuend"]),
        subtrahend=codec.deserialize(data["subtrahend"]),
        display=display_from_json(data["display"]),
    )


def _fraction_to(quantity: Quantity, codec: QuantityCodec) -> _Json:
    quantity = ensure_type(quantity, Fraction)
    return {
        "dividend": codec.serialize(quantity.dividend),
        "divisor": codec.serialize(quantity.divisor),
        "display": display_to_json(quantity.display),
    }


def _fraction_from(data: Mapping[str, object], codec: QuantityCodec) -> Fraction:
    return Fraction(
        dividend=codec.deserialize(data["dividend"]),
        divisor=codec.deserialize(data["divisor"]),
        display=display_from_json(data["display"]),
    )


def engine_quantity_codec(additional: QuantityCodec | None = None) -> QuantityCodec:
    # The standard engine quantities, optionally combined with a consumer's additional codec (e.g. the
    # pro quantities), so a caller never has to reconstruct the engine set.
    engine_specs = (
        QuantitySpec("rrd_metric", RRDMetric, _rrd_metric_to, _rrd_metric_from),
        QuantitySpec("constant", Constant, _constant_to, _constant_from),
        QuantitySpec("scalar_of", ScalarOf, _scalar_of_to, _scalar_of_from),
        QuantitySpec("sum", Sum, _sum_to, _sum_from),
        QuantitySpec("product", Product, _product_to, _product_from),
        QuantitySpec("difference", Difference, _difference_to, _difference_from),
        QuantitySpec("fraction", Fraction, _fraction_to, _fraction_from),
    )
    return QuantityCodec(
        engine_specs if additional is None else (*engine_specs, *additional._specs)
    )


def _curve_to_json(curve: Curve, codec: QuantityCodec) -> _Json:
    return {
        "quantity": codec.serialize(curve.quantity),
        "attributes": _attributes_to_json(curve.attributes),
    }


def _curve_from_json(data: object, codec: QuantityCodec) -> Curve:
    data = _as_mapping(data)
    return Curve(
        quantity=codec.deserialize(data["quantity"]),
        attributes=_attributes_from_json(data["attributes"]),
    )


def _stack_from_json(data: object, codec: QuantityCodec) -> Stack:
    data = _as_mapping(data)
    reference = data["reference"]
    return Stack(
        members=[_curve_from_json(member, codec) for member in _as_list(data["members"])],
        inverse=ensure_type(data["inverse"], bool),
        reference=None if reference is None else _curve_from_json(reference, codec),
    )


def _line_from_json(data: object, codec: QuantityCodec) -> Line:
    data = _as_mapping(data)
    return Line(
        curve=_curve_from_json(data["curve"], codec), inverse=ensure_type(data["inverse"], bool)
    )


def _rule_from_json(data: object, codec: QuantityCodec) -> Rule:
    data = _as_mapping(data)
    return Rule(
        curve=_curve_from_json(data["curve"], codec), inverse=ensure_type(data["inverse"], bool)
    )


def serialize_resolved_graph(graph: ResolvedGraph, codec: QuantityCodec | None = None) -> _Json:
    codec = engine_quantity_codec(codec)
    return {
        "name": graph.name,
        "title": graph.title,
        "graph_type": graph.graph_type,
        "vertical_range": (
            None if graph.vertical_range is None else _range_to_json(graph.vertical_range, codec)
        ),
        "stacks": [
            {
                "members": [_curve_to_json(member, codec) for member in stack.members],
                "inverse": stack.inverse,
                "reference": (
                    None if stack.reference is None else _curve_to_json(stack.reference, codec)
                ),
            }
            for stack in graph.stacks
        ],
        "lines": [
            {"curve": _curve_to_json(line.curve, codec), "inverse": line.inverse}
            for line in graph.lines
        ],
        "rules": [
            {"curve": _curve_to_json(rule.curve, codec), "inverse": rule.inverse}
            for rule in graph.rules
        ],
    }


def deserialize_resolved_graph(data: object, codec: QuantityCodec | None = None) -> ResolvedGraph:
    codec = engine_quantity_codec(codec)
    data = _as_mapping(data)
    vertical_range = data["vertical_range"]
    return ResolvedGraph(
        name=ensure_type(data["name"], str),
        title=ensure_type(data["title"], str),
        graph_type=ensure_type(data["graph_type"], str),
        vertical_range=(
            None if vertical_range is None else _range_from_json(vertical_range, codec)
        ),
        stacks=[_stack_from_json(stack, codec) for stack in _as_list(data["stacks"])],
        lines=[_line_from_json(line, codec) for line in _as_list(data["lines"])],
        rules=[_rule_from_json(rule, codec) for rule in _as_list(data["rules"])],
    )


def serialize_resolved_graphs(
    graphs: Sequence[ResolvedGraph], codec: QuantityCodec | None = None
) -> _Json:
    # Each resolved graph carries its own graph_type, so the envelope only holds the graph list.
    return {"graphs": [serialize_resolved_graph(graph, codec) for graph in graphs]}


def deserialize_resolved_graphs(
    data: Mapping[str, object], codec: QuantityCodec | None = None
) -> Sequence[ResolvedGraph]:
    return [deserialize_resolved_graph(graph, codec) for graph in _as_list(data["graphs"])]
