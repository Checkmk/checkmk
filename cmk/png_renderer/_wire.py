#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import assert_never

from ._model import (
    Area,
    AxisLabel,
    Legend,
    LegendRow,
    Line,
    PngDrawing,
    Region,
    RenderingFailure,
    Rule,
    Stack,
    TimeAxis,
    VerticalAxis,
)


def drawings_to_json(drawings: Sequence[PngDrawing]) -> str:
    return json.dumps({"drawings": [asdict(drawing) for drawing in drawings]})


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


def _ensure_type[T](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return value


def _optional_str(raw: object) -> str | None:
    return None if raw is None else _ensure_type(raw, str)


def _strs(raw: object) -> Sequence[str]:
    return [_ensure_type(value, str) for value in _ensure_type(raw, list)]


def _float(raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise TypeError(f"expected a number, got {type(raw).__name__}")
    return float(raw)


def _optional_float(raw: object) -> float | None:
    return None if raw is None else _float(raw)


def _optional_floats(raw: object) -> Sequence[float | None]:
    return [_optional_float(value) for value in _ensure_type(raw, list)]


def _ints(raw: object) -> Sequence[int]:
    return [_ensure_type(value, int) for value in _ensure_type(raw, list)]


def _int_pair(raw: object) -> tuple[int, int]:
    first, second = _ensure_type(raw, list)
    return _ensure_type(first, int), _ensure_type(second, int)


def _float_pair(raw: object) -> tuple[float, float]:
    first, second = _ensure_type(raw, list)
    return _float(first), _float(second)


def _area(raw: object) -> Area:
    fields = _ensure_type(raw, dict)
    return Area(color=_ensure_type(fields["color"], str), top=_optional_floats(fields["top"]))


def _stack(raw: object) -> Stack:
    fields = _ensure_type(raw, dict)
    return Stack(areas=[_area(area) for area in _ensure_type(fields["areas"], list)])


def _line(raw: object) -> Line:
    fields = _ensure_type(raw, dict)
    return Line(color=_ensure_type(fields["color"], str), values=_optional_floats(fields["values"]))


def _region(raw: object) -> Region:
    fields = _ensure_type(raw, dict)
    return Region(
        color=_ensure_type(fields["color"], str),
        lower=None if fields["lower"] is None else _optional_floats(fields["lower"]),
        upper=None if fields["upper"] is None else _optional_floats(fields["upper"]),
    )


def _rule(raw: object) -> Rule:
    fields = _ensure_type(raw, dict)
    return Rule(color=_ensure_type(fields["color"], str), value=_float(fields["value"]))


def _axis_label(raw: object) -> AxisLabel:
    fields = _ensure_type(raw, dict)
    return AxisLabel(position=_float(fields["position"]), text=_ensure_type(fields["text"], str))


def _vertical_axis(raw: object) -> VerticalAxis | None:
    if raw is None:
        return None
    labels = _ensure_type(raw, dict)["labels"]
    return VerticalAxis(
        labels=None
        if labels is None
        else [_axis_label(label) for label in _ensure_type(labels, list)]
    )


def _time_axis(raw: object) -> TimeAxis | None:
    if raw is None:
        return None
    return TimeAxis(time_zone=_optional_str(_ensure_type(raw, dict)["time_zone"]))


def _legend_row(raw: object) -> LegendRow:
    fields = _ensure_type(raw, dict)
    return LegendRow(color=_ensure_type(fields["color"], str), cells=_strs(fields["cells"]))


def _legend_rows(raw: object) -> Sequence[LegendRow]:
    return [_legend_row(row) for row in _ensure_type(raw, list)]


def _legend(raw: object) -> Legend | None:
    if raw is None:
        return None
    fields = _ensure_type(raw, dict)
    return Legend(
        height=_float(fields["height"]),
        header=_strs(fields["header"]),
        curves=_legend_rows(fields["curves"]),
        rules=_legend_rows(fields["rules"]),
        regions=_legend_rows(fields["regions"]),
    )


def _drawing(raw: object) -> PngDrawing:
    fields = _ensure_type(raw, dict)
    return PngDrawing(
        width_inches=_float(fields["width_inches"]),
        height_inches=_float(fields["height_inches"]),
        plot_height=_float(fields["plot_height"]),
        font_size=_float(fields["font_size"]),
        title=_optional_str(fields["title"]),
        caption=_optional_str(fields["caption"]),
        times=_ints(fields["times"]),
        x_range=_int_pair(fields["x_range"]),
        y_range=_float_pair(fields["y_range"]),
        stacks=[_stack(stack) for stack in _ensure_type(fields["stacks"], list)],
        lines=[_line(line) for line in _ensure_type(fields["lines"], list)],
        regions=[_region(region) for region in _ensure_type(fields["regions"], list)],
        rules=[_rule(rule) for rule in _ensure_type(fields["rules"], list)],
        vertical_axis=_vertical_axis(fields["vertical_axis"]),
        time_axis=_time_axis(fields["time_axis"]),
        legend=_legend(fields["legend"]),
    )


def drawings_from_json(text: str) -> Sequence[PngDrawing]:
    fields = _ensure_type(json.loads(text), dict)
    return [_drawing(drawing) for drawing in _ensure_type(fields["drawings"], list)]


def _png_result(raw: object) -> bytes | RenderingFailure:
    fields = _ensure_type(raw, dict)
    if "failure" in fields:
        return RenderingFailure(_ensure_type(fields["failure"], str))
    return base64.b64decode(_ensure_type(fields["png"], str))


def pngs_from_json(text: str) -> Sequence[bytes | RenderingFailure]:
    return [_png_result(raw) for raw in _ensure_type(json.loads(text), list)]
