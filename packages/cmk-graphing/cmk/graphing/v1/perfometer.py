#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .metric import Quantity


@dataclass(frozen=True)
class Closed:
    bound: int | float | Quantity


@dataclass(frozen=True)
class Open:
    bound: int | float | Quantity


@dataclass(frozen=True, kw_only=True)
class Perfometer:
    name: str
    upper_bound: Closed | Open
    lower_bound: Closed | Open
    segments: Sequence[Quantity]

    def __post_init__(self) -> None:
        assert self.name
        assert self.segments


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    name: str
    left: Perfometer
    right: Perfometer

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True, kw_only=True)
class Stacked:
    name: str
    upper: Perfometer
    lower: Perfometer

    def __post_init__(self) -> None:
        assert self.name


PerfometerType: TypeAlias = Perfometer | Bidirectional | Stacked
