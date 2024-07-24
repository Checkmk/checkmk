#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator
from typing import Final, Literal, NotRequired, TypedDict

from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage


class UnitInfo(TypedDict):
    title: str
    symbol: str
    render: Callable[[float], str]
    js_render: str
    id: NotRequired[str]
    stepping: NotRequired[str]
    color: NotRequired[str]
    graph_unit: NotRequired[Callable[[list[float]], tuple[str, list[str]]]]
    description: NotRequired[str]
    valuespec: NotRequired[
        type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage]
    ]
    conversion: NotRequired[Callable[[float], float]]
    perfometer_render: NotRequired[Callable[[float], str]]
    formatter_ident: NotRequired[
        Literal["Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"]
    ]


class UnitRegistry:
    def __init__(self) -> None:
        self.units: Final[dict[str, UnitInfo | Callable[[], UnitInfo]]] = {}

    def __getitem__(self, unit_id: str) -> UnitInfo:
        item = unit() if callable(unit := self.units[unit_id]) else unit
        item["id"] = unit_id
        item.setdefault("description", item["title"])
        return item

    def __setitem__(self, unit_id: str, unit: UnitInfo | Callable[[], UnitInfo]) -> None:
        self.units[unit_id] = unit

    def keys(self) -> Iterator[str]:
        yield from self.units

    def items(self) -> Iterator[tuple[str, UnitInfo]]:
        yield from ((key, self[key]) for key in self.keys())


# TODO: Refactor to plugin_registry structures
# Note: we cannot simply use dict[str, Callable[[], UnitInfo]] and refactor all unit registrations
# in our codebase because we need to stay compatible with custom extensions
unit_info = UnitRegistry()
