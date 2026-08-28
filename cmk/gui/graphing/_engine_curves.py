#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from cmk.graphing_engine import EvaluatedCurve, EvaluatedGraph
from cmk.graphing_engine import TimeRange as EngineTimeRange

from ._graph_metric_expressions import DrawnLineType, line_type_mirror, LineType


@dataclass(frozen=True, kw_only=True)
class DrawnCurve[CurveT]:
    curve: CurveT
    line_type: DrawnLineType
    mirrored: bool
    stack: str | None
    hidden: bool


class _DrawnStack[CurveT](Protocol):
    @property
    def members(self) -> Sequence[CurveT]: ...
    @property
    def reference(self) -> CurveT | None: ...
    @property
    def inverse(self) -> bool: ...


class _DrawnLine[CurveT](Protocol):
    @property
    def curve(self) -> CurveT: ...
    @property
    def inverse(self) -> bool: ...


def drawn_curves[CurveT](
    stacks: Sequence[_DrawnStack[CurveT]],
    lines: Sequence[_DrawnLine[CurveT]],
    *,
    include_reference: bool = False,
) -> Iterator[DrawnCurve[CurveT]]:
    """The curves of a graph in the order it draws them.

    A stack's reference is the baseline the renderer draws against, not a curve of its own, so it
    is yielded as hidden and only on request. A graph definition and an evaluated graph walk the
    same way.
    """
    for index, stack in enumerate(stacks):
        identifier = f"stack-{index}"
        opened = False
        if include_reference and stack.reference is not None:
            yield DrawnCurve(
                curve=stack.reference,
                line_type="area",
                mirrored=stack.inverse,
                stack=identifier,
                hidden=True,
            )
            opened = True
        for member in stack.members:
            yield DrawnCurve(
                curve=member,
                line_type="stack" if opened else "area",
                mirrored=stack.inverse,
                stack=identifier,
                hidden=False,
            )
            opened = True
    for line in lines:
        yield DrawnCurve(
            curve=line.curve,
            line_type="line",
            mirrored=line.inverse,
            stack=None,
            hidden=False,
        )


def serialize_drawn_curves[OutT](
    evaluated: EvaluatedGraph,
    to_output: Callable[[DrawnCurve[EvaluatedCurve]], OutT],
    *,
    fallback_time_range: EngineTimeRange,
    include_reference: bool = False,
) -> tuple[EngineTimeRange, list[OutT]]:
    """The drawn curves of an evaluated graph, and the time range their data came back on.

    The engine fetch aligns every series of a graph onto one shared grid, so the first curve's
    range is the graph's. A graph without curves reports the requested range.
    """
    outputs: list[OutT] = []
    time_range: EngineTimeRange | None = None
    for drawn in drawn_curves(
        evaluated.stacks, evaluated.lines, include_reference=include_reference
    ):
        if time_range is None:
            time_range = drawn.curve.time_series.time_range
        outputs.append(to_output(drawn))
    return fallback_time_range if time_range is None else time_range, outputs


def line_type_with_mirroring(line_type: DrawnLineType, mirrored: bool) -> LineType:
    """The line type spelled the way the legacy graph specifications and the API report it."""
    return line_type_mirror(line_type) if mirrored else line_type
