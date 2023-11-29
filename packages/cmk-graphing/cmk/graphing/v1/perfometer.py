#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from ._type_defs import Bound, Quantity

__all__ = [
    "Closed",
    "Open",
    "FocusRange",
    "Perfometer",
    "Bidirectional",
    "Stacked",
]


@dataclass(frozen=True)
class Closed:
    value: Bound

    def __post_init__(self) -> None:
        if isinstance(self.value, str) and not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class Open:
    value: Bound

    def __post_init__(self) -> None:
        if isinstance(self.value, str) and not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class FocusRange:
    lower: Closed | Open
    upper: Closed | Open


@dataclass(frozen=True)
class Perfometer:
    name: str
    focus_range: FocusRange
    segments: Sequence[Quantity]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.segments
        for s in self.segments:
            if isinstance(s, str) and not s:
                raise ValueError(s)


@dataclass(frozen=True)
class Bidirectional:
    name: str
    _: KW_ONLY
    left: Perfometer
    right: Perfometer

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class Stacked:
    name: str
    _: KW_ONLY
    lower: Perfometer
    upper: Perfometer

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
