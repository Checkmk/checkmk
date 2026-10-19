#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

type DrawnLineType = Literal["line", "area", "stack"]


@dataclass(frozen=True, kw_only=True)
class DrawnCurve[CurveT]:
    curve: CurveT
    line_type: DrawnLineType
    mirrored: bool
    stack: str | None


class _DrawnStack[CurveT](Protocol):
    @property
    def members(self) -> Sequence[CurveT]: ...
    @property
    def inverse(self) -> bool: ...


class _DrawnLine[CurveT](Protocol):
    @property
    def curve(self) -> CurveT: ...
    @property
    def inverse(self) -> bool: ...


def _drawn_stack[CurveT](
    members: Sequence[CurveT], identifier: str, mirrored: bool
) -> Iterator[DrawnCurve[CurveT]]:
    for position, curve in enumerate(members):
        yield DrawnCurve(
            curve=curve,
            line_type="stack" if position else "area",
            mirrored=mirrored,
            stack=identifier,
        )


def _drawn_lines[CurveT](lines: Sequence[_DrawnLine[CurveT]]) -> Iterator[DrawnCurve[CurveT]]:
    for line in lines:
        yield DrawnCurve(
            curve=line.curve,
            line_type="line",
            mirrored=line.inverse,
            stack=None,
        )


def drawn_curves[CurveT](
    stacks: Sequence[_DrawnStack[CurveT]], lines: Sequence[_DrawnLine[CurveT]]
) -> Iterator[DrawnCurve[CurveT]]:
    for index, stack in enumerate(stacks):
        yield from _drawn_stack(stack.members, f"stack-{index}", stack.inverse)
    yield from _drawn_lines(lines)
