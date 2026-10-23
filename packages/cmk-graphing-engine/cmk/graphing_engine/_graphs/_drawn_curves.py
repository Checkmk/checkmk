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
    inverse: bool
    stack: str | None


class _DrawnStackProtocol[CurveT](Protocol):
    @property
    def members(self) -> Sequence[CurveT]: ...
    @property
    def inverse(self) -> bool: ...


class _DrawnLineProtocol[CurveT](Protocol):
    @property
    def curve(self) -> CurveT: ...
    @property
    def inverse(self) -> bool: ...


def drawn_curves[CurveT](
    stacks: Sequence[_DrawnStackProtocol[CurveT]], lines: Sequence[_DrawnLineProtocol[CurveT]]
) -> Iterator[DrawnCurve[CurveT]]:
    for index, stack in enumerate(stacks):
        for position, curve in enumerate(stack.members):
            yield DrawnCurve(
                curve=curve,
                line_type="stack" if position else "area",
                inverse=stack.inverse,
                stack=f"stack-{index}",
            )
    for line in lines:
        yield DrawnCurve(curve=line.curve, line_type="line", inverse=line.inverse, stack=None)
