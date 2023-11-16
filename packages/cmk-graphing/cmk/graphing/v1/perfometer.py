#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from . import metric
from ._name import Name

__all__ = [
    "Name",
    "Closed",
    "Open",
    "Perfometer",
    "Bidirectional",
    "Stacked",
]


@dataclass(frozen=True)
class Closed:
    bound: int | float | metric.Quantity


@dataclass(frozen=True)
class Open:
    bound: int | float | metric.Quantity


@dataclass(frozen=True)
class Perfometer:
    name: Name
    segments: Sequence[metric.Quantity]
    _: KW_ONLY
    lower_bound: Closed | Open
    upper_bound: Closed | Open

    def __post_init__(self) -> None:
        assert self.segments


@dataclass(frozen=True)
class Bidirectional:
    name: Name
    _: KW_ONLY
    left: Perfometer
    right: Perfometer


@dataclass(frozen=True)
class Stacked:
    name: Name
    _: KW_ONLY
    lower: Perfometer
    upper: Perfometer
