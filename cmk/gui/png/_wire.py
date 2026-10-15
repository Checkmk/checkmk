#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import dataclasses
import json
from collections.abc import Mapping, Sequence
from typing import assert_never
from zoneinfo import ZoneInfo

from cmk.graphing_engine import (
    CurveAttributes,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRegion,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)
from cmk.gui.graphing import ensure_type, unit_from_specification, unit_to_specification
from cmk.gui.png.renderer import PngGraph, PngTexts, RenderingFailure
from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._size import PngOptions


def _attributes_to_json(attributes: CurveAttributes) -> Mapping[str, object]:
    return {
        "title": attributes.title,
        "unit": unit_to_specification(attributes.unit),
        "color": attributes.color,
    }


def _time_series_to_json(time_series: TimeSeries | None) -> Mapping[str, object] | None:
    if time_series is None:
        return None
    return {
        "time_range": dataclasses.asdict(time_series.time_range),
        "values": list(time_series.values),
    }


def _curve_to_json(curve: EvaluatedCurve | None) -> Mapping[str, object] | None:
    if curve is None:
        return None
    return {
        "id": curve.id,
        "attributes": _attributes_to_json(curve.attributes),
        "value": curve.value,
        "time_series": _time_series_to_json(curve.time_series),
        "source_id": curve.source_id,
        "series_attributes": {
            kind: dict(of_kind) for kind, of_kind in curve.series_attributes.items()
        },
    }


def _graph_to_json(graph: EvaluatedGraph) -> Mapping[str, object]:
    return {
        "name": graph.name,
        "title": graph.title,
        "time_range": dataclasses.asdict(graph.time_range),
        "vertical_range": (
            None if graph.vertical_range is None else dataclasses.asdict(graph.vertical_range)
        ),
        "stacks": [
            {
                "members": [_curve_to_json(member) for member in stack.members],
                "inverse": stack.inverse,
                "reference": _curve_to_json(stack.reference),
            }
            for stack in graph.stacks
        ],
        "lines": [
            {"curve": _curve_to_json(line.curve), "inverse": line.inverse} for line in graph.lines
        ],
        "rules": [
            {
                "id": rule.id,
                "attributes": _attributes_to_json(rule.attributes),
                "value": rule.value,
                "inverse": rule.inverse,
            }
            for rule in graph.rules
        ],
        "regions": [
            {
                "id": region.id,
                "attributes": _attributes_to_json(region.attributes),
                "lower": _time_series_to_json(region.lower),
                "upper": _time_series_to_json(region.upper),
            }
            for region in graph.regions
        ],
    }


def _png_graph_to_json(graph: PngGraph) -> Mapping[str, object]:
    return {
        "graph": _graph_to_json(graph.graph),
        "options": dataclasses.asdict(graph.options),
        "y_axis_unit": None
        if graph.y_axis_unit is None
        else unit_to_specification(graph.y_axis_unit),
        "requested_vertical_range": (
            None
            if graph.requested_vertical_range is None
            else dataclasses.asdict(graph.requested_vertical_range)
        ),
        "time_zone": (
            None if graph.time_zone is None else ensure_type(graph.time_zone, ZoneInfo).key
        ),
    }


def request_to_json(
    graphs: Sequence[PngGraph], texts: PngTexts, temperature_unit: TemperatureUnit
) -> str:
    return json.dumps(
        {
            "texts": dataclasses.asdict(texts),
            "temperature_unit": temperature_unit.value,
            "graphs": [_png_graph_to_json(graph) for graph in graphs],
        }
    )


def _png_result_to_json(result: bytes | RenderingFailure) -> Mapping[str, str]:
    match result:
        case bytes():
            return {"png": base64.b64encode(result).decode("ascii")}
        case RenderingFailure():
            return {"failure": result.message}
        case other:
            assert_never(other)


def pngs_to_json(results: Sequence[bytes | RenderingFailure]) -> str:
    return json.dumps([_png_result_to_json(result) for result in results])


def _optional_str(raw: object) -> str | None:
    return None if raw is None else ensure_type(raw, str)


def _float(raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise TypeError(f"expected a number, got {type(raw).__name__}")
    return float(raw)


def _optional_float(raw: object) -> float | None:
    return None if raw is None else _float(raw)


def _optional_floats(raw: object) -> list[float | None]:
    return [_optional_float(value) for value in ensure_type(raw, list)]


def _time_range(raw: object) -> TimeRange:
    fields = ensure_type(raw, dict)
    return TimeRange(
        start=ensure_type(fields["start"], int),
        end=ensure_type(fields["end"], int),
        step=ensure_type(fields["step"], int),
    )


def _time_series(raw: object) -> TimeSeries | None:
    if raw is None:
        return None
    fields = ensure_type(raw, dict)
    return TimeSeries(
        time_range=_time_range(fields["time_range"]), values=_optional_floats(fields["values"])
    )


def _unit(raw: object) -> Unit:
    unit = unit_from_specification(raw)
    if not isinstance(unit, Unit):
        raise TypeError("expected a convertible unit")
    return unit


def _attributes(raw: object) -> CurveAttributes:
    fields = ensure_type(raw, dict)
    return CurveAttributes(
        title=ensure_type(fields["title"], str),
        unit=_unit(fields["unit"]),
        color=ensure_type(fields["color"], str),
    )


def _series_attributes(raw: object) -> Mapping[str, Mapping[str, str]]:
    return {
        kind: {key: ensure_type(value, str) for key, value in ensure_type(of_kind, dict).items()}
        for kind, of_kind in ensure_type(raw, dict).items()
    }


def _curve(raw: object) -> EvaluatedCurve:
    fields = ensure_type(raw, dict)
    time_series = _time_series(fields["time_series"])
    if time_series is None:
        raise TypeError("expected the time series of a curve")
    return EvaluatedCurve(
        id=ensure_type(fields["id"], str),
        attributes=_attributes(fields["attributes"]),
        value=_optional_float(fields["value"]),
        time_series=time_series,
        source_id=_optional_str(fields["source_id"]),
        series_attributes=_series_attributes(fields["series_attributes"]),
    )


def _vertical_range(raw: object) -> EvaluatedVerticalRange | None:
    if raw is None:
        return None
    fields = ensure_type(raw, dict)
    return EvaluatedVerticalRange(
        range_kind=VerticalRangeKind(ensure_type(fields["range_kind"], str)),
        lower=_optional_float(fields["lower"]),
        upper=_optional_float(fields["upper"]),
    )


def _stack(raw: object) -> EvaluatedStack:
    fields = ensure_type(raw, dict)
    reference = fields["reference"]
    return EvaluatedStack(
        members=[_curve(member) for member in ensure_type(fields["members"], list)],
        inverse=ensure_type(fields["inverse"], bool),
        reference=None if reference is None else _curve(reference),
    )


def _line(raw: object) -> EvaluatedLine:
    fields = ensure_type(raw, dict)
    return EvaluatedLine(
        curve=_curve(fields["curve"]), inverse=ensure_type(fields["inverse"], bool)
    )


def _rule(raw: object) -> EvaluatedRule:
    fields = ensure_type(raw, dict)
    return EvaluatedRule(
        id=ensure_type(fields["id"], str),
        attributes=_attributes(fields["attributes"]),
        value=_float(fields["value"]),
        inverse=ensure_type(fields["inverse"], bool),
    )


def _region(raw: object) -> EvaluatedRegion:
    fields = ensure_type(raw, dict)
    return EvaluatedRegion(
        id=ensure_type(fields["id"], str),
        attributes=_attributes(fields["attributes"]),
        lower=_time_series(fields["lower"]),
        upper=_time_series(fields["upper"]),
    )


def _graph(raw: object) -> EvaluatedGraph:
    fields = ensure_type(raw, dict)
    return EvaluatedGraph(
        name=ensure_type(fields["name"], str),
        title=ensure_type(fields["title"], str),
        time_range=_time_range(fields["time_range"]),
        vertical_range=_vertical_range(fields["vertical_range"]),
        stacks=[_stack(stack) for stack in ensure_type(fields["stacks"], list)],
        lines=[_line(line) for line in ensure_type(fields["lines"], list)],
        rules=[_rule(rule) for rule in ensure_type(fields["rules"], list)],
        regions=[_region(region) for region in ensure_type(fields["regions"], list)],
    )


def _options(raw: object) -> PngOptions:
    fields = ensure_type(raw, dict)
    width, height = ensure_type(fields["size"], list)
    return PngOptions(
        size=(_float(width), _float(height)),
        font_size=_float(fields["font_size"]),
        show_title=ensure_type(fields["show_title"], bool),
        show_legend=ensure_type(fields["show_legend"], bool),
        show_vertical_axis=ensure_type(fields["show_vertical_axis"], bool),
        show_time_axis=ensure_type(fields["show_time_axis"], bool),
        show_graph_time=ensure_type(fields["show_graph_time"], bool),
    )


def _texts(raw: object) -> PngTexts:
    fields = ensure_type(raw, dict)
    return PngTexts(
        minimum=ensure_type(fields["minimum"], str),
        maximum=ensure_type(fields["maximum"], str),
        average=ensure_type(fields["average"], str),
        last=ensure_type(fields["last"], str),
        date_format=ensure_type(fields["date_format"], str),
        caption=ensure_type(fields["caption"], str),
    )


def _zone(raw: object) -> ZoneInfo | None:
    return None if raw is None else ZoneInfo(ensure_type(raw, str))


def _png_graph(raw: object) -> PngGraph:
    fields = ensure_type(raw, dict)
    y_axis_unit = fields["y_axis_unit"]
    return PngGraph(
        graph=_graph(fields["graph"]),
        options=_options(fields["options"]),
        y_axis_unit=None if y_axis_unit is None else unit_from_specification(y_axis_unit),
        requested_vertical_range=_vertical_range(fields["requested_vertical_range"]),
        time_zone=_zone(fields["time_zone"]),
    )


def request_from_json(text: str) -> tuple[Sequence[PngGraph], PngTexts, TemperatureUnit]:
    fields = ensure_type(json.loads(text), dict)
    return (
        [_png_graph(graph) for graph in ensure_type(fields["graphs"], list)],
        _texts(fields["texts"]),
        TemperatureUnit(ensure_type(fields["temperature_unit"], str)),
    )


def _png_result(raw: object) -> bytes | RenderingFailure:
    fields = ensure_type(raw, dict)
    if "failure" in fields:
        return RenderingFailure(ensure_type(fields["failure"], str))
    return base64.b64decode(ensure_type(fields["png"], str))


def pngs_from_json(text: str) -> Sequence[bytes | RenderingFailure]:
    return [_png_result(raw) for raw in ensure_type(json.loads(text), list)]
