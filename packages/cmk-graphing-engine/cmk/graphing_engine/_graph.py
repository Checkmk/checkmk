#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from ._quantity import Bound, Curve, MetricProtocol, QuantityProtocol
from ._title import title_metrics


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
    reference: Curve | None = None


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

    def _bound_quantities(self) -> Iterator[QuantityProtocol]:
        if self.vertical_range is None:
            return
        for bound in (self.vertical_range.lower, self.vertical_range.upper):
            if bound is not None and not isinstance(bound, int | float):
                yield bound

    def metrics(self) -> Sequence[MetricProtocol]:
        drawn = list(
            dict.fromkeys(
                metric
                for quantity in itertools.chain(
                    (m.quantity for g in self.stacks for m in g.members),
                    (g.reference.quantity for g in self.stacks if g.reference is not None),
                    (line.curve.quantity for line in self.lines),
                    (rule.curve.quantity for rule in self.rules),
                    self._bound_quantities(),
                )
                for metric in quantity.metrics()
            )
        )
        return list(dict.fromkeys([*drawn, *title_metrics(self.title, drawn)]))
