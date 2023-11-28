#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, field, KW_ONLY

from . import metric
from ._localize import Localizable
from ._type_defs import Bound, Quantity

__all__ = [
    "MinimalRange",
    "Graph",
    "Bidirectional",
]


@dataclass(frozen=True)
class MinimalRange:
    lower: Bound
    upper: Bound


@dataclass(frozen=True)
class Graph:
    name: str
    title: Localizable
    _: KW_ONLY
    minimal_range: MinimalRange | None = None
    compound_lines: Sequence[Quantity] = field(default_factory=list)
    simple_lines: Sequence[Quantity] = field(default_factory=list)
    optional: Sequence[metric.Name] = field(default_factory=list)
    conflicting: Sequence[metric.Name] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.compound_lines or self.simple_lines


@dataclass(frozen=True)
class Bidirectional:
    name: str
    title: Localizable
    _: KW_ONLY
    lower: Graph
    upper: Graph

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
