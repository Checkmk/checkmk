#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Final, Literal, NotRequired, TypedDict

from pydantic import BaseModel

from cmk.utils.metrics import MetricName

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage

from ._unit import ConvertibleUnitSpecification, NonConvertibleUnitSpecification, user_specific_unit

#   .--units---------------------------------------------------------------.
#   |                                    _ _                               |
#   |                        _   _ _ __ (_) |_ ___                         |
#   |                       | | | | '_ \| | __/ __|                        |
#   |                       | |_| | | | | | |_\__ \                        |
#   |                        \__,_|_| |_|_|\__|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class UnitInfoWithOrWithoutID(TypedDict):
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


@dataclass(frozen=True)
class UnitInfo:
    id: str
    title: str
    symbol: str
    render: Callable[[float], str]
    js_render: str
    conversion: Callable[[float], float]
    stepping: str | None = None
    color: str | None = None
    graph_unit: Callable[[list[float]], tuple[str, list[str]]] | None = None
    description: str | None = None
    valuespec: (
        type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage] | None
    ) = None
    perfometer_render: Callable[[float], str] | None = None


class UnitRegistry:
    def __init__(self) -> None:
        self.units: Final[
            dict[str, UnitInfoWithOrWithoutID | Callable[[], UnitInfoWithOrWithoutID]]
        ] = {}

    def __getitem__(self, unit_id: str) -> UnitInfo:
        item = unit() if callable(unit := self.units[unit_id]) else unit
        item.setdefault("description", item["title"])
        return UnitInfo(
            id=unit_id,
            title=item["title"],
            symbol=item["symbol"],
            render=item["render"],
            js_render=item["js_render"],
            stepping=item.get("stepping"),
            color=item.get("color"),
            graph_unit=item.get("graph_unit"),
            description=item.get("description", item["title"]),
            valuespec=item.get("valuespec"),
            conversion=item.get("conversion", lambda v: v),
            perfometer_render=item.get("perfometer_render"),
        )

    def __setitem__(
        self, unit_id: str, unit: UnitInfoWithOrWithoutID | Callable[[], UnitInfoWithOrWithoutID]
    ) -> None:
        self.units[unit_id] = unit

    def keys(self) -> Iterator[str]:
        yield from self.units

    def items(self) -> Iterator[tuple[str, UnitInfo]]:
        yield from ((key, self[key]) for key in self.keys())


# TODO: Refactor to plugin_registry structures
# Note: we cannot simply use dict[str, Callable[[], UnitInfo]] and refactor all unit registrations
# in our codebase because we need to stay compatible with custom extensions
unit_info = UnitRegistry()


class LegacyUnitSpecification(BaseModel, frozen=True):
    type: Literal["legacy"] = "legacy"
    id: str


def get_render_function(
    unit_spec: ConvertibleUnitSpecification | NonConvertibleUnitSpecification | UnitInfo,
) -> Callable[[float], str]:
    return (
        unit_spec.render
        if isinstance(unit_spec, UnitInfo)
        else user_specific_unit(unit_spec, user, active_config).formatter.render
    )


def get_conversion_function(
    unit_spec: ConvertibleUnitSpecification | NonConvertibleUnitSpecification | UnitInfo,
) -> Callable[[float], float]:
    return (
        unit_spec.conversion
        if isinstance(unit_spec, UnitInfo)
        else user_specific_unit(unit_spec, user, active_config).conversion
    )


def get_unit_info(unit_id: str) -> UnitInfo:
    if unit_id in unit_info.keys():
        return unit_info[unit_id]
    return unit_info[""]


# .
#   .--metrics-------------------------------------------------------------.
#   |                                _        _                            |
#   |                 _ __ ___   ___| |_ _ __(_) ___ ___                   |
#   |                | '_ ` _ \ / _ \ __| '__| |/ __/ __|                  |
#   |                | | | | | |  __/ |_| |  | | (__\__ \                  |
#   |                |_| |_| |_|\___|\__|_|  |_|\___|___/                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class _MetricInfoMandatory(TypedDict):
    title: str | LazyString
    unit: str
    color: str


class MetricInfo(_MetricInfoMandatory, total=False):
    help: str | LazyString
    render: Callable[[float | int], str]


metric_info: dict[MetricName, MetricInfo] = {}


# .
#   .--translations--------------------------------------------------------.
#   |        _                       _       _   _                         |
#   |       | |_ _ __ __ _ _ __  ___| | __ _| |_(_) ___  _ __  ___         |
#   |       | __| '__/ _` | '_ \/ __| |/ _` | __| |/ _ \| '_ \/ __|        |
#   |       | |_| | | (_| | | | \__ \ | (_| | |_| | (_) | | | \__ \        |
#   |        \__|_|  \__,_|_| |_|___/_|\__,_|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CheckMetricEntry(TypedDict, total=False):
    scale: float
    name: MetricName
    auto_graph: bool
    deprecated: str


check_metrics: dict[str, dict[MetricName, CheckMetricEntry]] = {}
