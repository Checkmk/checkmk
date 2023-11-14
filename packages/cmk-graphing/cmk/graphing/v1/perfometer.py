#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from .metric import Quantity


@dataclass(frozen=True)
class Closed:
    bound: int | float | Quantity


@dataclass(frozen=True)
class Open:
    bound: int | float | Quantity


@dataclass(frozen=True)
class Perfometer:
    name: str
    segments: Sequence[Quantity]
    _: KW_ONLY
    upper_bound: Closed | Open
    lower_bound: Closed | Open

    def __post_init__(self) -> None:
        assert self.name
        assert self.segments


@dataclass(frozen=True)
class Bidirectional:
    name: str
    _: KW_ONLY
    left: Perfometer
    right: Perfometer

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class Stacked:
    name: str
    _: KW_ONLY
    upper: Perfometer
    lower: Perfometer

    def __post_init__(self) -> None:
        assert self.name
