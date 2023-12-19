#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, field

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

    def __post_init__(self) -> None:
        if isinstance(self.lower, str) and not self.lower:
            raise ValueError(self.lower)
        if isinstance(self.upper, str) and not self.upper:
            raise ValueError(self.upper)


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: Localizable
    minimal_range: MinimalRange | None = None
    compound_lines: Sequence[Quantity] = field(default_factory=list)
    simple_lines: Sequence[Quantity] = field(default_factory=list)
    optional: Sequence[str] = field(default_factory=list)
    conflicting: Sequence[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.compound_lines or self.simple_lines
        for c in self.compound_lines:
            if isinstance(c, str) and not c:
                raise ValueError(c)
        for s in self.simple_lines:
            if isinstance(s, str) and not s:
                raise ValueError(s)
        for o in self.optional:
            if isinstance(o, str) and not o:
                raise ValueError(o)
        for c in self.conflicting:
            if isinstance(c, str) and not c:
                raise ValueError(c)


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    name: str
    title: Localizable
    lower: Graph
    upper: Graph

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
