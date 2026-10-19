#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from cmk.graphing_engine._data._units import CurveAttributes
from cmk.graphing_engine._quantities._quantity import fetch_leaves, MetricProtocol, QuantityProtocol

# What a drawable is bounded by: a plain number, or a quantity to be evaluated.
type Bound = int | float | QuantityProtocol


@dataclass(frozen=True, kw_only=True)
class Curve:
    """A quantity dressed for drawing: what to evaluate, and how to title, scale and colour it."""

    quantity: QuantityProtocol
    attributes: CurveAttributes
    source_id: str | None = None


@dataclass(frozen=True)
class MinimalRange:
    lower: Bound | None
    upper: Bound | None


@dataclass(frozen=True)
class FixedRange:
    lower: Bound | None
    upper: Bound | None


type VerticalRange = MinimalRange | FixedRange


@dataclass(frozen=True)
class Stack:
    members: Sequence[Curve]
    inverse: bool


@dataclass(frozen=True)
class Region:
    lower: Curve | None
    upper: Curve | None
    attributes: CurveAttributes


@dataclass(frozen=True)
class Line:
    curve: Curve
    inverse: bool


@dataclass(frozen=True)
class Rule:
    curve: Curve
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: str
    kind: str
    vertical_range: VerticalRange | None = None
    # Drop the curves with nothing to see - all zero, or no data at all - instead of drawing them.
    omit_zero_curves: bool = False
    stacks: Sequence[Stack] = ()
    lines: Sequence[Line] = ()
    rules: Sequence[Rule] = ()
    regions: Sequence[Region] = ()

    def _bound_quantities(self) -> Iterator[QuantityProtocol]:
        if self.vertical_range is None:
            return
        for bound in (self.vertical_range.lower, self.vertical_range.upper):
            if bound is not None and not isinstance(bound, int | float):
                yield bound

    def drawn_quantities(self) -> Iterator[tuple[QuantityProtocol, bool]]:
        for group in self.stacks:
            for member in group.members:
                yield member.quantity, group.inverse
        for line in self.lines:
            yield line.curve.quantity, line.inverse

    def curves(self) -> Iterator[Curve]:
        for stack in self.stacks:
            yield from stack.members
        for line in self.lines:
            yield line.curve
        for rule in self.rules:
            yield rule.curve
        for region in self.regions:
            if region.lower is not None:
                yield region.lower
            if region.upper is not None:
                yield region.upper

    def metrics(self) -> Sequence[MetricProtocol]:
        return list(
            dict.fromkeys(
                metric
                for quantity in itertools.chain(
                    (curve.quantity for curve in self.curves()),
                    self._bound_quantities(),
                )
                for metric in fetch_leaves(quantity)
            )
        )
