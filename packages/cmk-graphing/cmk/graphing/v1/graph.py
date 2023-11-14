#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, field, KW_ONLY

from ._localize import Localizable
from .metric import MetricName, Quantity


@dataclass(frozen=True, kw_only=True)
class MinimalRange:
    upper: int | float | Quantity
    lower: int | float | Quantity


@dataclass(frozen=True)
class Graph:
    name: str
    title: Localizable
    _: KW_ONLY
    minimal_range: MinimalRange | None = None
    compound_lines: Sequence[Quantity] = field(default_factory=list)
    simple_lines: Sequence[Quantity] = field(default_factory=list)
    optional: Sequence[MetricName] = field(default_factory=list)
    conflicting: Sequence[MetricName] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert self.name
        assert self.compound_lines or self.simple_lines


@dataclass(frozen=True)
class Bidirectional:
    name: str
    title: Localizable
    _: KW_ONLY
    upper: Graph
    lower: Graph

    def __post_init__(self) -> None:
        assert self.name
