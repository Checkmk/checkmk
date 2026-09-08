#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
    TimeRange,
    Unit,
)


def ensure_type[T](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return value


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"expected a mapping, got {type(value).__name__}")
    return value


def _as_list(value: object) -> Sequence[object]:
    if not isinstance(value, list):
        raise TypeError(f"expected a list, got {type(value).__name__}")
    return value


def _as_number(value: object) -> int | float:
    if not isinstance(value, int | float):
        raise TypeError(f"expected a number, got {type(value).__name__}")
    return value


# QuantityProtocol is an open protocol spanning packages, and the engine must stay serialization-free, so the
# codec is an external registry keyed by kind: it dispatches on each quantity's own kind() forward and
# on the serialized kind reverse. The engine layer registers its own quantities below; the pro layer
# composes its aggregation quantities on top.


@dataclass(frozen=True)
class QuantitySpec:
    kind: str
    to_dict: Callable[[QuantityProtocol, QuantityCodec], Mapping[str, object]]
    from_dict: Callable[[Mapping[str, object], QuantityCodec], QuantityProtocol]


class QuantityCodec:
    def __init__(self, specs: Sequence[QuantitySpec]) -> None:
        # Two quantities claiming one kind would make the later spec silently decide how the earlier
        # one is read back, so refuse the codec instead of mis-deserializing at request time.
        self._by_kind: dict[str, QuantitySpec] = {}
        for spec in specs:
            if spec.kind in self._by_kind:
                raise ValueError(f"duplicate quantity kind: {spec.kind}")
            self._by_kind[spec.kind] = spec

    def kinds(self) -> Sequence[str]:
        return tuple(self._by_kind)

    def serialize(self, quantity: QuantityProtocol) -> Mapping[str, object]:
        kind = quantity.kind()
        return {"kind": kind, **self._by_kind[kind].to_dict(quantity, self)}

    def deserialize(self, data: object) -> QuantityProtocol:
        data = _as_mapping(data)
        return self._by_kind[ensure_type(data["kind"], str)].from_dict(data, self)


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


def _unit_to_json(unit: Unit) -> Mapping[str, object]:
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


def _attributes_to_json(attributes: CurveAttributes) -> Mapping[str, object]:
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


def _display_to_json(display: CurveAttributes | None) -> Mapping[str, object] | None:
    return None if display is None else _attributes_to_json(display)


def _display_from_json(data: object) -> CurveAttributes | None:
    return None if data is None else _attributes_from_json(data)


def _rrd_metric_to_json(quantity: QuantityProtocol, _codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, RRDMetric)
    return {
        "site_id": quantity.site_id,
        "host_name": quantity.host_name,
        "service_name": quantity.service_name,
        "metric_name": str(quantity.metric_name),
        "consolidation_function": (
            None
            if quantity.consolidation_function is None
            else str(quantity.consolidation_function)
        ),
    }


def _rrd_metric_from_json(data: Mapping[str, object], _codec: QuantityCodec) -> RRDMetric:
    consolidation_function = data["consolidation_function"]
    site_id = data.get("site_id")
    return RRDMetric(
        site_id=None if site_id is None else SiteID(ensure_type(site_id, str)),
        host_name=HostName(ensure_type(data["host_name"], str)),
        service_name=ServiceName(ensure_type(data["service_name"], str)),
        metric_name=MetricName(ensure_type(data["metric_name"], str)),
        consolidation_function=(
            None
            if consolidation_function is None
            else ConsolidationFunction(ensure_type(consolidation_function, str))
        ),
    )


def _constant_to_json(quantity: QuantityProtocol, _codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, Constant)
    return {"value": quantity.value, "display": _display_to_json(quantity.display)}


def _constant_from_json(data: Mapping[str, object], _codec: QuantityCodec) -> Constant:
    return Constant(_as_number(data["value"]), _display_from_json(data["display"]))


def _scalar_of_to_json(quantity: QuantityProtocol, codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, ScalarOf)
    return {
        "metric": codec.serialize(quantity.metric),
        "scalar_kind": str(quantity.scalar_kind),
        "color": quantity.color,
    }


def _scalar_of_from_json(data: Mapping[str, object], codec: QuantityCodec) -> ScalarOf:
    color = data["color"]
    if color is not None and not isinstance(color, str):
        raise TypeError(f"expected a string or None, got {type(color).__name__}")
    return ScalarOf(
        metric=ensure_type(codec.deserialize(data["metric"]), RRDMetric),
        scalar_kind=ScalarKind(ensure_type(data["scalar_kind"], str)),
        color=color,
    )


def _operands_to_json(
    operands: Sequence[QuantityProtocol], codec: QuantityCodec
) -> Sequence[Mapping[str, object]]:
    return [codec.serialize(operand) for operand in operands]


def _operands_from_json(data: object, codec: QuantityCodec) -> Sequence[QuantityProtocol]:
    return [codec.deserialize(operand) for operand in _as_list(data)]


def _sum_to_json(quantity: QuantityProtocol, codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, Sum)
    return {
        "summands": _operands_to_json(quantity.summands, codec),
        "display": _display_to_json(quantity.display),
    }


def _sum_from_json(data: Mapping[str, object], codec: QuantityCodec) -> Sum:
    return Sum(_operands_from_json(data["summands"], codec), _display_from_json(data["display"]))


def _product_to_json(quantity: QuantityProtocol, codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, Product)
    return {
        "factors": _operands_to_json(quantity.factors, codec),
        "display": _display_to_json(quantity.display),
    }


def _product_from_json(data: Mapping[str, object], codec: QuantityCodec) -> Product:
    return Product(_operands_from_json(data["factors"], codec), _display_from_json(data["display"]))


def _difference_to_json(quantity: QuantityProtocol, codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, Difference)
    return {
        "minuend": codec.serialize(quantity.minuend),
        "subtrahend": codec.serialize(quantity.subtrahend),
        "display": _display_to_json(quantity.display),
    }


def _difference_from_json(data: Mapping[str, object], codec: QuantityCodec) -> Difference:
    return Difference(
        minuend=codec.deserialize(data["minuend"]),
        subtrahend=codec.deserialize(data["subtrahend"]),
        display=_display_from_json(data["display"]),
    )


def _fraction_to_json(quantity: QuantityProtocol, codec: QuantityCodec) -> Mapping[str, object]:
    quantity = ensure_type(quantity, Fraction)
    return {
        "dividend": codec.serialize(quantity.dividend),
        "divisor": codec.serialize(quantity.divisor),
        "display": _display_to_json(quantity.display),
    }


def _fraction_from_json(data: Mapping[str, object], codec: QuantityCodec) -> Fraction:
    return Fraction(
        dividend=codec.deserialize(data["dividend"]),
        divisor=codec.deserialize(data["divisor"]),
        display=_display_from_json(data["display"]),
    )


class GraphCodec:
    def __init__(self, quantities: QuantityCodec) -> None:
        self._quantities = quantities

    def quantity_kinds(self) -> Sequence[str]:
        # The quantity kinds this codec can carry. The engine owns the quantities but not their
        # transport, so a quantity gaining a field cannot break the build - only a round-trip test
        # catches it. Tests use this to assert every registered kind has such a test.
        return self._quantities.kinds()

    def serialize_quantity(self, quantity: QuantityProtocol) -> Mapping[str, object]:
        return self._quantities.serialize(quantity)

    def deserialize_quantity(self, data: object) -> QuantityProtocol:
        return self._quantities.deserialize(data)

    def _bound_to_json(self, bound: int | float | QuantityProtocol) -> Mapping[str, object]:
        if isinstance(bound, int | float):
            return {"kind": "number", "value": bound}
        return {"kind": "quantity", "quantity": self._quantities.serialize(bound)}

    def _bound_from_json(self, data: object) -> int | float | QuantityProtocol:
        data = _as_mapping(data)
        if data["kind"] == "number":
            return _as_number(data["value"])
        return self._quantities.deserialize(data["quantity"])

    def _range_to_json(self, vertical_range: MinimalRange | FixedRange) -> Mapping[str, object]:
        return {
            "kind": "minimal" if isinstance(vertical_range, MinimalRange) else "fixed",
            "lower": None
            if vertical_range.lower is None
            else self._bound_to_json(vertical_range.lower),
            "upper": None
            if vertical_range.upper is None
            else self._bound_to_json(vertical_range.upper),
        }

    def _range_from_json(self, data: object) -> MinimalRange | FixedRange:
        data = _as_mapping(data)
        cls = MinimalRange if data["kind"] == "minimal" else FixedRange
        lower = data["lower"]
        upper = data["upper"]
        return cls(
            lower=None if lower is None else self._bound_from_json(lower),
            upper=None if upper is None else self._bound_from_json(upper),
        )

    def _curve_to_json(self, curve: Curve) -> Mapping[str, object]:
        return {
            "quantity": self._quantities.serialize(curve.quantity),
            "attributes": _attributes_to_json(curve.attributes),
            "source_id": curve.source_id,
        }

    def _curve_from_json(self, data: object) -> Curve:
        data = _as_mapping(data)
        source_id = data.get("source_id")
        return Curve(
            quantity=self._quantities.deserialize(data["quantity"]),
            attributes=_attributes_from_json(data["attributes"]),
            source_id=None if source_id is None else ensure_type(source_id, str),
        )

    def _stack_to_json(self, stack: Stack) -> Mapping[str, object]:
        return {
            "members": [self._curve_to_json(member) for member in stack.members],
            "inverse": stack.inverse,
            "reference": (
                None if stack.reference is None else self._curve_to_json(stack.reference)
            ),
        }

    def _stack_from_json(self, data: object) -> Stack:
        data = _as_mapping(data)
        reference = data["reference"]
        return Stack(
            members=[self._curve_from_json(member) for member in _as_list(data["members"])],
            inverse=ensure_type(data["inverse"], bool),
            reference=None if reference is None else self._curve_from_json(reference),
        )

    def _line_to_json(self, line: Line) -> Mapping[str, object]:
        return {"curve": self._curve_to_json(line.curve), "inverse": line.inverse}

    def _line_from_json(self, data: object) -> Line:
        data = _as_mapping(data)
        return Line(
            curve=self._curve_from_json(data["curve"]), inverse=ensure_type(data["inverse"], bool)
        )

    def _rule_to_json(self, rule: Rule) -> Mapping[str, object]:
        return {"curve": self._curve_to_json(rule.curve), "inverse": rule.inverse}

    def _rule_from_json(self, data: object) -> Rule:
        data = _as_mapping(data)
        return Rule(
            curve=self._curve_from_json(data["curve"]), inverse=ensure_type(data["inverse"], bool)
        )

    def serialize_graph(self, graph: Graph) -> Mapping[str, object]:
        return {
            "name": graph.name,
            "title": graph.title,
            "kind": graph.kind,
            "vertical_range": (
                None if graph.vertical_range is None else self._range_to_json(graph.vertical_range)
            ),
            "omit_zero_curves": graph.omit_zero_curves,
            "stacks": [self._stack_to_json(stack) for stack in graph.stacks],
            "lines": [self._line_to_json(line) for line in graph.lines],
            "rules": [self._rule_to_json(rule) for rule in graph.rules],
        }

    def deserialize_graph(self, data: object) -> Graph:
        data = _as_mapping(data)
        vertical_range = data["vertical_range"]
        return Graph(
            name=ensure_type(data["name"], str),
            title=ensure_type(data["title"], str),
            kind=ensure_type(data["kind"], str),
            vertical_range=(
                None if vertical_range is None else self._range_from_json(vertical_range)
            ),
            omit_zero_curves=ensure_type(data["omit_zero_curves"], bool),
            stacks=[self._stack_from_json(stack) for stack in _as_list(data["stacks"])],
            lines=[self._line_from_json(line) for line in _as_list(data["lines"])],
            rules=[self._rule_from_json(rule) for rule in _as_list(data["rules"])],
        )

    def serialize_graphs(self, graphs: Sequence[Graph]) -> Mapping[str, object]:
        return {"graphs": [self.serialize_graph(graph) for graph in graphs]}

    def deserialize_graphs(self, data: Mapping[str, object]) -> Sequence[Graph]:
        return [self.deserialize_graph(graph) for graph in ensure_type(data["graphs"], list)]


def graph_codec(specs: Sequence[QuantitySpec]) -> GraphCodec:
    return GraphCodec(QuantityCodec(specs))


# What this edition can carry: the engine's own quantities. Every edition on top of it extends this
# set, so a graph written by a smaller edition stays readable by a bigger one.
COMMUNITY_QUANTITY_SPECS: Sequence[QuantitySpec] = (
    QuantitySpec("rrd_metric", _rrd_metric_to_json, _rrd_metric_from_json),
    QuantitySpec("constant", _constant_to_json, _constant_from_json),
    QuantitySpec("scalar_of", _scalar_of_to_json, _scalar_of_from_json),
    QuantitySpec("sum", _sum_to_json, _sum_from_json),
    QuantitySpec("product", _product_to_json, _product_from_json),
    QuantitySpec("difference", _difference_to_json, _difference_from_json),
    QuantitySpec("fraction", _fraction_to_json, _fraction_from_json),
)


def community_graph_codec() -> GraphCodec:
    # One codec per edition rather than one per graph kind: a definition may hold a quantity another
    # kind introduced - a combined aggregation inside a custom graph - and every kind has to be able to
    # read it back.
    return graph_codec(COMMUNITY_QUANTITY_SPECS)


def consolidation_function_of(options: Mapping[str, object]) -> ConsolidationFunction:
    return ensure_type(options["consolidation_function"], ConsolidationFunction)


def time_range_of(options: Mapping[str, object]) -> TimeRange:
    return ensure_type(options["time_range"], TimeRange)
